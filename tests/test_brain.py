import json, unittest
from bot.brain import Brain, BrainError

# Fake RosterMap: accetta un insieme fisso di nomi/ruoli, come build_payload si aspetta.
class FakeRoster:
    RUOLI = {**{f"P{i}": "P" for i in range(3)}, **{f"D{i}": "D" for i in range(8)},
             **{f"C{i}": "C" for i in range(8)}, **{f"A{i}": "A" for i in range(6)}}
    def resolve(self, nome, require_owned=True):
        if nome not in self.RUOLI:
            raise ValueError(f"'{nome}' non è nella tua rosa")
        # build_payload usa `pid, role = rm.resolve(n)`: resolve ritorna una tupla (id, ruolo).
        return (abs(hash(nome)) % 100000, self.RUOLI[nome])

def _spec_valido():
    tit = ["P0"] + [f"D{i}" for i in range(3)] + [f"C{i}" for i in range(4)] + [f"A{i}" for i in range(3)]
    panca = ["P1", "P2"] + [f"D{i}" for i in range(3, 8)] + [f"C{i}" for i in range(4, 8)] + ["A3"]
    return {"modulo": "343", "titolari": tit, "panchina": panca, "capitano": []}

def _risposta_gemini(spec):
    testo = "Ragionamento...\n" + json.dumps(spec)
    return {"candidates": [{"content": {"parts": [{"text": testo}]},
                            "groundingMetadata": {"webSearchQueries": ["probabili giornata 4"]}}]}

class TestBrain(unittest.TestCase):
    def test_proponi_valido_al_primo_colpo(self):
        chiamate = []
        def fake_post(url, headers, body):
            chiamate.append(json.loads(body))
            return _risposta_gemini(_spec_valido())
        b = Brain("k", "gemini-3.6-flash", rm=FakeRoster(), http_post=fake_post)
        spec = b.proponi("TABELLA", 4)
        self.assertEqual(spec["modulo"], "343")
        self.assertEqual(len(chiamate), 1)
        # il tool google_search è nel corpo della richiesta
        self.assertIn("google_search", json.dumps(chiamate[0]))

    def test_proponi_riprova_su_spec_invalido(self):
        invalido = dict(_spec_valido(), titolari=["P0"] * 11)  # 11 portieri: reparti incoerenti
        seq = [_risposta_gemini(invalido), _risposta_gemini(_spec_valido())]
        def fake_post(url, headers, body):
            return seq.pop(0)
        b = Brain("k", "m", rm=FakeRoster(), http_post=fake_post)
        spec = b.proponi("T", 4)
        self.assertEqual(spec, _spec_valido())
        self.assertEqual(seq, [])  # ha consumato entrambe: 1 invalida + 1 valida

    def test_errore_dopo_max_tentativi(self):
        invalido = dict(_spec_valido(), titolari=["P0"] * 11)
        def fake_post(url, headers, body):
            return _risposta_gemini(invalido)
        b = Brain("k", "m", max_tentativi=3, rm=FakeRoster(), http_post=fake_post)
        with self.assertRaises(BrainError):
            b.proponi("T", 4)

    def test_modifica_passa_richiesta_e_spec_precedente(self):
        catturato = {}
        def fake_post(url, headers, body):
            catturato["body"] = json.loads(body)
            return _risposta_gemini(_spec_valido())
        b = Brain("k", "m", rm=FakeRoster(), http_post=fake_post)
        b.modifica(_spec_valido(), "gioca il 352 con A3 titolare", "T", 4)
        corpo = json.dumps(catturato["body"])
        self.assertIn("352", corpo)
        self.assertIn("A3", corpo)
        self.assertIn("343", corpo)  # modulo dello spec precedente nel body

    def test_errore_su_candidates_vuoti(self):
        def fake_post(url, headers, body):
            return {"candidates": []}
        b = Brain("k", "m", max_tentativi=2, rm=FakeRoster(), http_post=fake_post)
        with self.assertRaises(BrainError):
            b.proponi("T", 4)

class TestBrainCalendario(unittest.TestCase):
    def _brain(self, testo):
        self.body = {}
        def fake_post(url, headers, body):
            self.body = json.loads(body)
            return {"candidates": [{"content": {"parts": [{"text": testo}]}}]}
        return Brain("k", "m", rm=FakeRoster(), http_post=fake_post)

    def test_calendario_intera_giornata(self):
        # Calendario COMPLETO del turno: il primo kickoff (l'anticipo) e' il deadline.
        b = self._brain('Ecco il calendario: '
                        '[{"partita":"Venezia-Fiorentina","kickoff":"2026-09-11T20:45"},'
                        '{"partita":"Inter-Udinese","kickoff":"2026-09-14T20:45"}]')
        cal = b.calendario(4)
        self.assertEqual(len(cal), 2)
        self.assertEqual(cal[0]["kickoff"], "2026-09-11T20:45")

    def test_calendario_chiede_tutte_le_partite(self):
        b = self._brain("[]")
        b.calendario(4)
        # Il prompt deve chiedere TUTTE le partite del turno, non solo le mie squadre.
        self.assertIn("tutte le partite", json.dumps(self.body).lower())

    def test_calendario_json_illeggibile_ritorna_vuoto(self):
        b = self._brain("nessun array JSON qui")
        self.assertEqual(b.calendario(4), [])

    def test_calendario_filtra_voci_senza_kickoff(self):
        b = self._brain('[{"partita":"Inter-Udinese","kickoff":"2026-09-12T20:45"}, {"foo":1}, "x"]')
        cal = b.calendario(4)
        self.assertEqual(cal, [{"partita": "Inter-Udinese", "kickoff": "2026-09-12T20:45"}])

if __name__ == "__main__":
    unittest.main()
