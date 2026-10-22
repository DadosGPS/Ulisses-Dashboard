"""Imitação mínima do Supabase Auth para os testes das páginas.

Gera uma chave ES256 ao arrancar, escreve em e2e/sessao.json um token válido
(e o cookie de sessão que o @supabase/ssr espera) e responde a:
  GET /auth/v1/.well-known/jwks.json  → chave pública (usada pela API)
  GET /auth/v1/user                   → utilizador do token (usado pela web)
  GET /rest/v1/team_members           → equipas do utilizador (a única consulta
                                        que a web faz diretamente ao Supabase)
Uso: python e2e/auth_falso.py [porta]
"""
import base64
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 54321
AQUI = os.path.dirname(os.path.abspath(__file__))
USER = "00000000-0000-0000-0000-0000000000e2"
EMAIL = "pf@teste.e2e"

chave = ec.generate_private_key(ec.SECP256R1())
jwk = json.loads(ECAlgorithm.to_jwk(chave.public_key()))
jwk.update({"kid": "e2e", "alg": "ES256", "use": "sig"})
agora = int(time.time())
UTILIZADOR = {"id": USER, "aud": "authenticated", "role": "authenticated", "email": EMAIL,
              "app_metadata": {"provider": "email"}, "user_metadata": {"nome": "PF Teste"},
              "created_at": "2026-01-01T00:00:00Z"}
token = jwt.encode({"sub": USER, "email": EMAIL, "aud": "authenticated", "role": "authenticated",
                    "iat": agora, "exp": agora + 6 * 3600}, chave, algorithm="ES256", headers={"kid": "e2e"})
sessao = {"access_token": token, "refresh_token": "e2e", "token_type": "bearer", "expires_in": 6 * 3600,
          "expires_at": agora + 6 * 3600, "user": UTILIZADOR}
json.dump({"token": token, "cookie": "base64-" + base64.urlsafe_b64encode(json.dumps(sessao).encode()).decode().rstrip("=")},
          open(os.path.join(AQUI, "sessao.json"), "w"))


class Pedido(BaseHTTPRequestHandler):
    def _json(self, codigo, corpo):
        dados = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self._cors()
        self.end_headers()
        self.wfile.write(dados)

    def _cors(self):
        # O browser também fala com o Supabase diretamente (como em produção).
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin") or "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "*, authorization, apikey, content-type, x-client-info, accept-profile")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/auth/v1/.well-known/jwks.json"):
            return self._json(200, {"keys": [jwk]})
        if self.path.startswith("/auth/v1/user"):
            cab = self.headers.get("Authorization", "")
            try:
                jwt.decode(cab.removeprefix("Bearer ").strip(), chave.public_key(), algorithms=["ES256"], audience="authenticated")
            except jwt.PyJWTError:
                return self._json(401, {"code": 401, "msg": "invalid JWT"})
            return self._json(200, UTILIZADOR)
        if self.path.startswith("/rest/v1/team_members"):
            from urllib.parse import parse_qs, urlparse

            import psycopg2
            uid = (parse_qs(urlparse(self.path).query).get("user_id") or ["eq."])[0].removeprefix("eq.")
            with psycopg2.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
                cur.execute("select team_id::text from team_members where user_id::text = %s order by (select nome from teams t where t.id = team_id)", (uid,))
                return self._json(200, [{"team_id": t} for (t,) in cur.fetchall()])
        return self._json(404, {"msg": "not found"})

    def do_POST(self):
        return self._json(404, {"msg": "not found"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"auth falso em http://127.0.0.1:{PORTA}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORTA), Pedido).serve_forever()
