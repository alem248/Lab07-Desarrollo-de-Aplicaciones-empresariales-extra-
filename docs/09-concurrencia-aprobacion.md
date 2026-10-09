# Paso 9 — Flujo de aprobación segura y concurrencia

## 1. Solicitud de eliminación de los comentarios del artículo 5

El artículo 5 es «Reseña: festival de cine andino»
(1 comentario). Se pide la eliminación **sin** aprobar:

```console
$ python manage.py agent --intent '{"action": "delete_comments_of_post", "args": {"post_id": 20}}'
{
  "status": "approval_required",
  "plan": {
    "action": "delete_comments_of_post",
    "args": {"post_id": 20},
    "details": {"affected_comment_ids": [39]},
    "plan_hash": "838daacb5fbb"
  }
}
No se aplicó nada. Si TÚ apruebas este plan, repite el comando con --approve 838daacb5fbb
```

> Nota: SQLite con `AUTOINCREMENT` no reutiliza los `id`,
> así que cada `seed_blog` mueve el artículo 5 a un `id`
> nuevo (20, 35, ...). Por eso el demo resuelve el `id`
> por título antes de cada paso.

## 2. Confirmación con `--approve` y persistencia

```console
$ python manage.py agent --intent '{"action": "delete_comments_of_post", "args": {"post_id": 20}}' --approve 838daacb5fbb
{
  "status": "applied",
  "plan": { ... "plan_hash": "838daacb5fbb" },
  "result": {"deleted": 1}
}
```

Verificación de persistencia: el comentario **desaparece**
de la base de datos (`Comment.objects.filter(post_id=20).count()`
pasa de **1 a 0**). La operación se ejecuta dentro de una
transacción atómica (`transaction.atomic`), por lo que se
aplica completa o nada.

## 3. Restauración determinista

```console
$ python manage.py seed_blog
Listo: 4 autores, 15 artículos, 23 comentarios.
```

El estado vuelve a ser el de referencia (23 comentarios;
el artículo «Reseña: festival de cine andino» tiene 1
otra vez).

## 4. Simulación de concurrencia: un comentario llega entre el plan y la aprobación

Se genera un plan, **luego** un usuario inserta un comentario
nuevo, y **después** un humano intenta aprobar con el hash
antes obtenido:

```console
$ python manage.py agent --intent '{"action": "delete_comments_of_post", "args": {"post_id": 35}}'
{
  "status": "approval_required",
  "plan": {
    "action": "delete_comments_of_post",
    "args": {"post_id": 35},
    "details": {"affected_comment_ids": [62]},
    "plan_hash": "f05f68176c35"
  }
}
>>>> plan_hash (estado que el humano miró): f05f68176c35

>>> Comment.objects.create(post_id=35, author_name="Lector nuevo",
                           text="Comentario llegado tarde")
>>>> comentarios ahora (mutó la base): 2

$ python manage.py agent --intent '{"action": "delete_comments_of_post", "args": {"post_id": 35}}' --approve f05f68176c35
{
  "status": "approval_required",
  "plan": {
    "action": "delete_comments_of_post",
    "args": {"post_id": 35},
    "details": {"affected_comment_ids": [62, 70]},
    "plan_hash": "005fc21e1309"
  }
}
>>>> estado: approval_required (el hash viejo ya no protege el estado nuevo)
>>>> comentarios siguen ahí: 2
```

**La aprobación con el hash obsoleto no borra nada**: el
estado sigue siendo `approval_required`, el plan se
reconstruye del estado **actual** (ahora con dos
comentarios: `[62, 70]`) y su hash es distinto
(`005fc21e1309` ≠ `f05f68176c35`).

## Por qué se invalida el hash criptográfico

El `plan_hash` no es un identificador arbitrario: es un
**resumen criptográfico del contenido exacto del plan**.

1. **Qué se hashea.** `plan_hash()` canonaliza con
   `json.dumps(..., sort_keys=True)` el objeto
   `{"action": ..., "args": ..., "details": ...}` y calcula
   `sha256(...)[:12]`. Cualquier bit distinto en la entrada
   produce un hash distinto (propiedad de avalancha de
   SHA-256).
2. **Qué contiene `details`.** El plan se construye **en el
   momento de la decisión** con `action.plan(**args)`, que
   lee la base de datos **actual**: la lista
   `affected_comment_ids` es el conjunto real de filas que
   la operación tocaría *ahora*.
3. **La mutación concurrente cambia la entrada.** Al
   insertarse el comentario 70, `details` pasa de
   `{"affected_comment_ids": [62]}` a
   `{"affected_comment_ids": [62, 70]}`; el JSON canónico
   cambia y, con él, el hash.
4. **La comparación es contra el estado vivo.** Al aprobar,
   `execute` **no** confía en el hash que llegó: recalcula
   el plan del estado actual y solo aplica si
   `approval == digest` del plan **recién calculado**. El
   hash antiguo describe un estado que ya no existe, por lo
   que resulta «inservible» (`approval_required` con un
   nuevo hash).
5. **Consecuencia de seguridad.** Un aprobante humano solo
   puede autorizar el alcance exacto que vio. Si alguien
   (o algún proceso, o el propio modelo) altera los datos
   entre la visualización y la aprobación —añade un
   comentario, borra otro, cambia un `post_id`— la
   aprobación caduca y la operación exige revisión de
   nuevo. Es el patrón **optimistic concurrency control**
   aplicado a la gobernanza de acciones de un LLM: la
   intención del modelo nunca es suficiente, y el
   consentimiento humano solo es válido para el estado que
   fue aprobado.

## Pruebas que lo respaldan

`blog/tests/test_agent.py` codifica el comportamiento:

- `test_a_human_approval_of_the_exact_plan_applies_it`:
  la aprobación del hash exacto aplica la operación.
- `test_the_approval_dies_if_the_data_changed_after_the_human_looked`:
  si cambia la base tras generar el hash, la aprobación
  muere (`approval_required`) y los comentarios siguen ahí.
- `test_an_approval_for_another_plan_is_worthless`:
  un hash inventado (`000000000000`) no autoriza nada.
