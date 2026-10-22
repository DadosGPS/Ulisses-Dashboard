"""Dados fictícios para os testes das páginas: 1 academia, Sub-15 e Sub-16,
14 jogadores cada, 6 semanas de sessões GPS, microciclos, testes T1 e jogos.
Datas relativas a hoje, para as páginas terem sempre dados «recentes»."""
import json
import os
import random
import sys
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import execute_values

random.seed(3)
URL = os.environ["DATABASE_URL"]
USER = "00000000-0000-0000-0000-0000000000e2"
c = psycopg2.connect(URL); c.autocommit = True; cur = c.cursor()

cur.execute("insert into auth.users (id, email, raw_user_meta_data) values (%s, 'pf@teste.e2e', %s) on conflict do nothing",
            (USER, json.dumps({"nome": "PF Teste"})))
cur.execute("insert into profiles (id, nome) values (%s, 'PF Teste') on conflict do nothing", (USER,))
cur.execute("delete from teams where criado_por = %s", (USER,))  # equipa vazia criada no registo
cur.execute("insert into academias (nome) values ('Academia de Teste') returning id"); acad = cur.fetchone()[0]
cur.execute("insert into academia_membros (academia_id, user_id, papel) values (%s, %s, 'head')", (acad, USER))

hoje = date.today()
epoca_ini = hoje.year if hoje.month >= 7 else hoje.year - 1
epoca = f"{epoca_ini}/{str(epoca_ini + 1)[-2:]}"
segunda = hoje - timedelta(days=hoje.weekday())
ini = segunda - timedelta(weeks=5)
POS = ["GR", "DC", "DC", "LD", "LE", "MC", "MC", "MO", "EX", "EX", "PL", "PL", "MC", "DC"]
equipas = {}
for esc, ano in (("Sub-15", epoca_ini - 14), ("Sub-16", epoca_ini - 15)):
    cur.execute("insert into teams (nome, criado_por, academia_id, escalao, epoca) values (%s, %s, %s, %s, %s) returning id",
                (f"{esc} · {epoca}", USER, acad, esc, epoca)); tid = cur.fetchone()[0]; equipas[esc] = str(tid)
    cur.execute("insert into team_members (team_id, user_id, role) values (%s, %s, 'owner') on conflict do nothing", (tid, USER))
    for s in range(10):  # 6 semanas passadas + 4 por vir
        d0 = ini + timedelta(weeks=s)
        fase = "Pré-época" if s < 2 else "1.ª volta"
        perfil = ["Introdutório", "Carga", "Competitivo", "Choque", "Competitivo", "Recuperação"][s % 6]
        dias = {(d0 + timedelta(days=6)).isoformat(): {"tipo": "Jogo", "dia_md": "MD", "objetivo": f"vs Adversário {s + 1}"}}
        cur.execute("""insert into microciclos (team_id, numero, data_inicio, data_fim, perfil, fase, fatores, dias)
                       values (%s, %s, %s, %s, %s, %s, '{"distancia": 2.5, "hsr": 2.0, "sprint": 1.5}', %s::jsonb)""",
                    (tid, s + 1, d0, d0 + timedelta(days=6), perfil, fase, json.dumps(dias)))
    sessoes, avals, jogadores = [], [], []
    for j in range(14):
        nome = f"{esc} Jogador {j + 1:02d}"
        nasc = date(ano, 1 + j % 12, 1 + j % 27)
        cur.execute("""insert into atletas (academia_id, nome, data_nascimento, altura_pai_cm, altura_mae_cm)
                       values (%s, %s, %s, %s, %s) returning id""",
                    (acad, nome, nasc, random.randint(170, 188), random.randint(156, 172))); aid = cur.fetchone()[0]
        cur.execute("insert into players (team_id, nome, posicao, atleta_id) values (%s, %s, %s, %s) returning id",
                    (tid, nome, POS[j], aid)); pid = cur.fetchone()[0]; jogadores.append(aid)
        d = ini
        while d <= hoje:
            dow = d.weekday()
            if dow != 0:
                jogo = dow == 6
                md = {1: "MD-5", 2: "MD-4", 3: "MD-3", 4: "MD-2", 5: "MD-1", 6: "MD"}[dow]
                dur = 80 if jogo else random.randint(55, 85)
                dist = random.uniform(7000, 9000) if jogo else dur * random.uniform(80, 110)
                pse = random.randint(7, 9) if jogo else random.randint(3, 8)
                sessoes.append((tid, pid, d, "Jogo" if jogo else "Treino", md, (d - ini).days // 7 + 1, round(dist),
                                round(dist * random.uniform(.04, .09)), round(dist * random.uniform(.005, .02)),
                                random.randint(20, 60), random.randint(20, 60), round(random.uniform(26, 32), 1),
                                pse, dur, pse * dur, random.randint(8, 18), 3, 3, 3, 3))
            d += timedelta(days=1)
        dia_t = ini + timedelta(days=9)
        for k, v in {"altura_cm": random.gauss(165, 7), "peso_kg": random.gauss(54, 6), "sprint_10m_s": random.gauss(1.9, .06),
                     "sprint_30m_s": random.gauss(4.5, .12), "corrida_1km_s": random.gauss(225, 10), "cmj_cm": random.gauss(33, 3)}.items():
            avals.append((acad, aid, tid, dia_t, k, round(v, 2), 1))
    execute_values(cur, """insert into gps_sessions (team_id, player_id, data, tipo, dia_md, microciclo_nr, distancia_total_m,
        hsr_m, sprint_m, acc_n, dcc_n, vel_max_kmh, pse_sessao, duracao_min, carga_interna, hooper_index, sono, dor_musc,
        stress, humor) values %s""", sessoes)
    execute_values(cur, "insert into avaliacoes (academia_id, atleta_id, team_id, data, metrica, valor, momento) values %s", avals)
    # Exercícios registados no GPS (médias por jogador de cada exercício).
    exs = []
    for k in range(30):
        d = ini + timedelta(days=1 + k)
        if d.weekday() in (0, 6) or d > hoje:
            continue
        for nome, cat, dur, dpm, hpm, spm in (("Rondo 5v2", "Rondo", 12, 62, 0.4, 0), ("Jogo reduzido 4v4", "Jogo reduzido", 16, 105, 4.5, 0.6),
                                             ("Finalização em vagas", "Finalização", 15, 80, 6.0, 2.2)):
            f = random.uniform(0.9, 1.1)
            exs.append((tid, d, nome, cat, dur, 14, round(dur * dpm * f), round(dur * hpm * f), round(dur * spm * f),
                        round(dur * 0.8 * f), round(dur * 0.7 * f), random.randint(4, 8)))
    execute_values(cur, """insert into exercises (team_id, data, exercicio, categoria, duracao_min, n_jogadores, distancia_total_m,
        hsr_m, sprint_m, acc_n, dcc_n, pse_exercicio) values %s""", exs)
    for n, dj in enumerate((ini + timedelta(days=6), ini + timedelta(days=13)), start=1):
        cur.execute("""insert into jogos (academia_id, team_id, data, competicao, adversario, numero, duracao_min, golos_marcados, golos_sofridos)
                       values (%s, %s, %s, 'Campeonato', %s, %s, 80, 2, 1) returning id""", (acad, tid, dj, f"Adversário {n}", n))
        jid = cur.fetchone()[0]
        for i, aid in enumerate(jogadores):
            cur.execute("""insert into jogo_participacoes (jogo_id, atleta_id, titular, minutos, golos, assistencias)
                           values (%s, %s, %s, %s, %s, 0)""", (jid, aid, i < 11, 80 if i < 11 else 20, 1 if i == 10 else 0))

cur.execute("""insert into exercicios_biblioteca (academia_id, nome, categoria, formato, espaco, duracao_min, manual)
               values (%s, 'Rondo 5v2', 'Rondo', '5v2', '12×12 m', 12, '{}'), (%s, 'Circuito de força', 'Físico / velocidade', null, null, 20, '{"distancia": 40, "acc": 0.3}')""",
            (acad, acad))
json.dump({"user": USER, "equipas": equipas}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados.json"), "w"))
print("semeado:", equipas, file=sys.stderr)
