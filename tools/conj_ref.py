# -*- coding: utf-8 -*-
"""Reference conjugation table: 9 verbs x 6 tenses x 6 persons.
Written by hand so the agent pass can be diffed against it instead of trusted."""
import json, os

P = ["je", "tu", "il/elle", "nous", "vous", "ils/elles"]
T = ["Present", "PasseCompose", "Imparfait", "FuturSimple", "Conditionnel", "Subjonctif"]

C = {
 "etre": {
  "inf": "être", "pp": "été", "aux": "avoir",
  "Present": ["je suis", "tu es", "il/elle est", "nous sommes", "vous êtes", "ils/elles sont"],
  "PasseCompose": ["j'ai été", "tu as été", "il/elle a été", "nous avons été", "vous avez été", "ils/elles ont été"],
  "Imparfait": ["j'étais", "tu étais", "il/elle était", "nous étions", "vous étiez", "ils/elles étaient"],
  "FuturSimple": ["je serai", "tu seras", "il/elle sera", "nous serons", "vous serez", "ils/elles seront"],
  "Conditionnel": ["je serais", "tu serais", "il/elle serait", "nous serions", "vous seriez", "ils/elles seraient"],
  "Subjonctif": ["que je sois", "que tu sois", "qu'il/elle soit", "que nous soyons", "que vous soyez", "qu'ils/elles soient"],
 },
 "avoir": {
  "inf": "avoir", "pp": "eu", "aux": "avoir",
  "Present": ["j'ai", "tu as", "il/elle a", "nous avons", "vous avez", "ils/elles ont"],
  "PasseCompose": ["j'ai eu", "tu as eu", "il/elle a eu", "nous avons eu", "vous avez eu", "ils/elles ont eu"],
  "Imparfait": ["j'avais", "tu avais", "il/elle avait", "nous avions", "vous aviez", "ils/elles avaient"],
  "FuturSimple": ["j'aurai", "tu auras", "il/elle aura", "nous aurons", "vous aurez", "ils/elles auront"],
  "Conditionnel": ["j'aurais", "tu aurais", "il/elle aurait", "nous aurions", "vous auriez", "ils/elles auraient"],
  "Subjonctif": ["que j'aie", "que tu aies", "qu'il/elle ait", "que nous ayons", "que vous ayez", "qu'ils/elles aient"],
 },
 "aller": {
  "inf": "aller", "pp": "allé", "aux": "être",
  "Present": ["je vais", "tu vas", "il/elle va", "nous allons", "vous allez", "ils/elles vont"],
  "PasseCompose": ["je suis allée", "tu es allé(e)", "il est allé / elle est allée",
                   "nous sommes allé(e)s", "vous êtes allé(e)(s)", "ils sont allés / elles sont allées"],
  "Imparfait": ["j'allais", "tu allais", "il/elle allait", "nous allions", "vous alliez", "ils/elles allaient"],
  "FuturSimple": ["j'irai", "tu iras", "il/elle ira", "nous irons", "vous irez", "ils/elles iront"],
  "Conditionnel": ["j'irais", "tu irais", "il/elle irait", "nous irions", "vous iriez", "ils/elles iraient"],
  "Subjonctif": ["que j'aille", "que tu ailles", "qu'il/elle aille", "que nous allions", "que vous alliez", "qu'ils/elles aillent"],
 },
 "faire": {
  "inf": "faire", "pp": "fait", "aux": "avoir",
  "Present": ["je fais", "tu fais", "il/elle fait", "nous faisons", "vous faites", "ils/elles font"],
  "PasseCompose": ["j'ai fait", "tu as fait", "il/elle a fait", "nous avons fait", "vous avez fait", "ils/elles ont fait"],
  "Imparfait": ["je faisais", "tu faisais", "il/elle faisait", "nous faisions", "vous faisiez", "ils/elles faisaient"],
  "FuturSimple": ["je ferai", "tu feras", "il/elle fera", "nous ferons", "vous ferez", "ils/elles feront"],
  "Conditionnel": ["je ferais", "tu ferais", "il/elle ferait", "nous ferions", "vous feriez", "ils/elles feraient"],
  "Subjonctif": ["que je fasse", "que tu fasses", "qu'il/elle fasse", "que nous fassions", "que vous fassiez", "qu'ils/elles fassent"],
 },
 "pouvoir": {
  "inf": "pouvoir", "pp": "pu", "aux": "avoir",
  "Present": ["je peux", "tu peux", "il/elle peut", "nous pouvons", "vous pouvez", "ils/elles peuvent"],
  "PasseCompose": ["j'ai pu", "tu as pu", "il/elle a pu", "nous avons pu", "vous avez pu", "ils/elles ont pu"],
  "Imparfait": ["je pouvais", "tu pouvais", "il/elle pouvait", "nous pouvions", "vous pouviez", "ils/elles pouvaient"],
  "FuturSimple": ["je pourrai", "tu pourras", "il/elle pourra", "nous pourrons", "vous pourrez", "ils/elles pourront"],
  "Conditionnel": ["je pourrais", "tu pourrais", "il/elle pourrait", "nous pourrions", "vous pourriez", "ils/elles pourraient"],
  "Subjonctif": ["que je puisse", "que tu puisses", "qu'il/elle puisse", "que nous puissions", "que vous puissiez", "qu'ils/elles puissent"],
 },
 "vouloir": {
  "inf": "vouloir", "pp": "voulu", "aux": "avoir",
  "Present": ["je veux", "tu veux", "il/elle veut", "nous voulons", "vous voulez", "ils/elles veulent"],
  "PasseCompose": ["j'ai voulu", "tu as voulu", "il/elle a voulu", "nous avons voulu", "vous avez voulu", "ils/elles ont voulu"],
  "Imparfait": ["je voulais", "tu voulais", "il/elle voulait", "nous voulions", "vous vouliez", "ils/elles voulaient"],
  "FuturSimple": ["je voudrai", "tu voudras", "il/elle voudra", "nous voudrons", "vous voudrez", "ils/elles voudront"],
  "Conditionnel": ["je voudrais", "tu voudrais", "il/elle voudrait", "nous voudrions", "vous voudriez", "ils/elles voudraient"],
  "Subjonctif": ["que je veuille", "que tu veuilles", "qu'il/elle veuille", "que nous voulions", "que vous vouliez", "qu'ils/elles veuillent"],
 },
 "devoir": {
  "inf": "devoir", "pp": "dû", "aux": "avoir",
  "Present": ["je dois", "tu dois", "il/elle doit", "nous devons", "vous devez", "ils/elles doivent"],
  "PasseCompose": ["j'ai dû", "tu as dû", "il/elle a dû", "nous avons dû", "vous avez dû", "ils/elles ont dû"],
  "Imparfait": ["je devais", "tu devais", "il/elle devait", "nous devions", "vous deviez", "ils/elles devaient"],
  "FuturSimple": ["je devrai", "tu devras", "il/elle devra", "nous devrons", "vous devrez", "ils/elles devront"],
  "Conditionnel": ["je devrais", "tu devrais", "il/elle devrait", "nous devrions", "vous devriez", "ils/elles devraient"],
  "Subjonctif": ["que je doive", "que tu doives", "qu'il/elle doive", "que nous devions", "que vous deviez", "qu'ils/elles doivent"],
 },
 "venir": {
  "inf": "venir", "pp": "venu", "aux": "être",
  "Present": ["je viens", "tu viens", "il/elle vient", "nous venons", "vous venez", "ils/elles viennent"],
  "PasseCompose": ["je suis venue", "tu es venu(e)", "il est venu / elle est venue",
                   "nous sommes venu(e)s", "vous êtes venu(e)(s)", "ils sont venus / elles sont venues"],
  "Imparfait": ["je venais", "tu venais", "il/elle venait", "nous venions", "vous veniez", "ils/elles venaient"],
  "FuturSimple": ["je viendrai", "tu viendras", "il/elle viendra", "nous viendrons", "vous viendrez", "ils/elles viendront"],
  "Conditionnel": ["je viendrais", "tu viendrais", "il/elle viendrait", "nous viendrions", "vous viendriez", "ils/elles viendraient"],
  "Subjonctif": ["que je vienne", "que tu viennes", "qu'il/elle vienne", "que nous venions", "que vous veniez", "qu'ils/elles viennent"],
 },
 "prendre": {
  "inf": "prendre", "pp": "pris", "aux": "avoir",
  "Present": ["je prends", "tu prends", "il/elle prend", "nous prenons", "vous prenez", "ils/elles prennent"],
  "PasseCompose": ["j'ai pris", "tu as pris", "il/elle a pris", "nous avons pris", "vous avez pris", "ils/elles ont pris"],
  "Imparfait": ["je prenais", "tu prenais", "il/elle prenait", "nous prenions", "vous preniez", "ils/elles prenaient"],
  "FuturSimple": ["je prendrai", "tu prendras", "il/elle prendra", "nous prendrons", "vous prendrez", "ils/elles prendront"],
  "Conditionnel": ["je prendrais", "tu prendrais", "il/elle prendrait", "nous prendrions", "vous prendriez", "ils/elles prendraient"],
  "Subjonctif": ["que je prenne", "que tu prennes", "qu'il/elle prenne", "que nous prenions", "que vous preniez", "qu'ils/elles prennent"],
 },
}

# what TTS should read when the printed cell carries optional-letter notation
SAY = {
 "tu es allé(e)": "tu es allé",
 "nous sommes allé(e)s": "nous sommes allés",
 "vous êtes allé(e)(s)": "vous êtes allés",
 "il est allé / elle est allée": "il est allé, elle est allée",
 "ils sont allés / elles sont allées": "ils sont allés, elles sont allées",
 "tu es venu(e)": "tu es venu",
 "nous sommes venu(e)s": "nous sommes venus",
 "vous êtes venu(e)(s)": "vous êtes venus",
 "il est venu / elle est venue": "il est venu, elle est venue",
 "ils sont venus / elles sont venues": "ils sont venus, elles sont venues",
}

if __name__ == "__main__":
    n = 0
    for v in C:
        for t in T:
            assert len(C[v][t]) == 6, (v, t)
            n += 6
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conj_ref.json")
    json.dump({"persons": P, "tenses": T, "verbs": C, "say": SAY},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("forms:", n, "->", out)
