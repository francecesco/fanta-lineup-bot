import os, tempfile, unittest
from bot.settings import carica_settings, Settings

class TestSettings(unittest.TestCase):
    def _env(self, righe):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(righe))
        self.addCleanup(os.remove, path)
        return path

    def test_carica_segreti_e_default(self):
        env = self._env([
            "FANTA_USER=cesco", "FANTA_PWD=segreta",
            "GEMINI_API_KEY=AQ.xxx", "TELEGRAM_BOT_TOKEN=123:abc",
            "TELEGRAM_CHAT_ID=999",
        ])
        s = carica_settings(env)
        self.assertIsInstance(s, Settings)
        self.assertEqual(s.fanta_user, "cesco")
        self.assertEqual(s.telegram_chat_id, "999")
        self.assertEqual(s.gemini_model, "gemini-3.6-flash")
        self.assertEqual(s.buffer_invio_min, 30)          # default
        self.assertEqual(s.ora_heartbeat, "08:00")        # default
        self.assertIn(s.lega["idcomp"], (s.lega["idcomp"],))  # presa da config.LEGA

    def test_manca_un_segreto_errore_chiaro(self):
        env = self._env(["FANTA_USER=cesco"])  # mancano gli altri
        with self.assertRaises(ValueError) as ctx:
            carica_settings(env)
        self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
