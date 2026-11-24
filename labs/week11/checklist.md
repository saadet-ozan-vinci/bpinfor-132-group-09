# Week 11 checklist

## In session

### Block 1, the guards (8 to 40)

- [ ] You read all twelve legitimate messages BEFORE writing any pattern
- [ ] TODO 1a and 1b done, and you wrote the plurals (`instructions?`)
- [ ] TODO 2 done, and you can say in one line what an output guard can
      actually prevent
- [ ] TODO 3 done, and its rule reports a CATEGORY, never the matched string
- [ ] `01_measure.py` runs and writes `artifacts/guard_events.jsonl`
- [ ] For every guard you can state catch rate AND false block count. Never
      one without the other.
- [ ] You can name the legitimate message your tighter guard blocks, and say
      whether you would ship that

### Block 2, layers and fail modes (40 to 65)

- [ ] `02_layers.py` run, and you can name the attacks that pass every guard
- [ ] You can say what the survivors have in common, and why another pattern
      will not fix it
- [ ] You can say which guard PREVENTS rather than detects, and why
- [ ] The fail mode demonstration run, and you chose open or closed for each
      of your own guards deliberately
- [ ] You can say what `fail_mode_triggered` is for, and why it is not the
      same as `fired`

### Block 3, the gates (65 to 85)

- [ ] TODO 4a and 4b done, and `pytest -q` is green
- [ ] You broke each gate on purpose and watched it fail
- [ ] Your guard events store no payloads. Check by grepping the file for
      your own attack strings.

### Close (85 to 90)

- [ ] `DECISIONS.md` written, with both numbers beside every guard
- [ ] Committed and pushed

## Homework

- [ ] One attack of your own that defeats every guard you built
- [ ] One legitimate message that your guards wrongly block
- [ ] Both in `traffic.py` with a note saying what they are for

## The three things a demonstrator will ask

1. What does your tighter guard cost a real user? Name the message.
2. Show me an attack that passes everything, and tell me what would stop it.
   If your answer is "a better regex", try writing it and run the corpus.
3. One of your guards throws at 3am. What happens, and where is that written
   down?
