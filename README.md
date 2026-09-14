# pokemarkov

A Markov chain trained on ~1,000 real Pokémon names, in a Databricks notebook, with a widget that lets you watch it pick each letter.

Training is one `groupBy().count()`. That's not a simplification, that's the whole thing.

## Run it

```bash
python invent_a_pokemon.py
```

Writes `invent_a_pokemon.html` — open it in any browser. Paste the same file into a Databricks cell and it calls `displayHTML` instead. Needs `requests` for PokéAPI; falls back to an embedded gen 1–2 list if the API is unreachable, so it always works.

## What's in the widget

- **Memory toggle** (1/2/3 letters of context) — order 2 invents, order 3 plagiarizes. That's overfitting, with a switch.
- **Chaos slider** — temperature, the same one on every LLM API. Drag it and the probability bars flatten and sharpen live.
- **Most likely** — greedy decoding. Same name every time, at every temperature, forever.
- **Verdict badge** — brand new / one letter from something real / already exists. The middle one exists because the first version called *Zigzagon* original with a straight face.
- **Provenance** — which training names the fragments came from. At order 3 it's usually one name, which is the point.
- **Bits per letter** — surprisal of each choice, tinted teal to coral. Also known as cross-entropy, also known as the number every language model is trained to push down.

## Swap the corpus

Nothing here knows what a Pokémon is. Replace `names` with city names, dinosaur species, Hungarian villages, your product catalog. Only the vibes change.

---

Pokémon names used as a public dataset for educational purposes; Pokémon is a trademark of Nintendo / Creatures / Game Freak. *Flaafaikou*, however, is legally mine.
