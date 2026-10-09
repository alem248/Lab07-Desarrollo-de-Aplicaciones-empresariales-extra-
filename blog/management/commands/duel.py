from django.core.management.base import BaseCommand, CommandError

from blog.duel.questions import BY_KEY
from blog.duel.runner import SOURCES, STATUS_LABEL, run_all


class Command(BaseCommand):
    help = "Corre las ocho preguntas del duelo contra tus respuestas (o las de la IA)."

    def _allow_unicode_output(self):
        """Print any text safely on any console.

        The status markers are ASCII and the question text is
        cp1252-safe, but a Windows console defaults to cp1252 and
        any other non-ASCII character would kill the command with
        `UnicodeEncodeError`. The stream is reconfigured in place
        (Python 3.7+); the `StringIO` that tests pass has no
        `reconfigure` and is left untouched.
        """
        stream = self.stdout._out
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=sorted(SOURCES), default="team",
                            help="de quién son las respuestas (por defecto: team = las tuyas)")
        parser.add_argument("--question", choices=sorted(BY_KEY),
                            help="correr solo una pregunta, p. ej. q4")
        parser.add_argument("--strict", action="store_true",
                            help="terminar con error si alguna no es correcta")

    def handle(self, *args, **options):
        self._allow_unicode_output()
        try:
            verdicts = run_all(options["source"], options["question"])
        except ModuleNotFoundError as exc:
            raise CommandError(f"No hay respuestas de «{options['source']}»: {exc}") from exc

        self.stdout.write(f"\nDuelo — respuestas de: {options['source']}\n")
        for verdict in verdicts:
            question = BY_KEY[verdict.key]
            queries = f"{verdict.queries} consulta(s)" if verdict.status != "todo" else ""
            self.stdout.write(
                f"{verdict.key}  {STATUS_LABEL[verdict.status]:<24} {queries:<16}"
                f"{question.text[:60]}"
            )
            if verdict.detail:
                self.stdout.write(f"      -> {verdict.detail}")

        good = sum(1 for verdict in verdicts if verdict.status == "ok")
        self.stdout.write(f"\n{good} de {len(verdicts)} correctas y baratas.\n")
        if options["strict"] and good != len(verdicts):
            raise CommandError("Hay respuestas que no son correctas.")
