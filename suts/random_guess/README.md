# random_guess reference SUT — the measured chance line

Keyless, **stateless** reference SUT for `symbolic_associative_retention`. It
learns nothing and retains nothing: every RECALL probe is answered with a
uniformly random attribute and every TRANSFER probe with a uniformly random bin,
drawn from the task's own vocabulary. It never touches the survive-dir and keeps
no in-RAM memory, so it scores the same at every point of the reset axis.

## Why the ladder needs it

`no_state` floors at `R(k) = 0.000` because it answers `unknown` rather than
guessing — an honest floor for a program, but one that invites the obvious
objection: *your floor SUT declines to answer; a real system would guess.* A
model will guess. This rung answers that directly by putting the chance line on
the same measured axis as everything else.

The rung also exists because the chance line used to be dangerously high. Before
RB-16 the task had two attributes and two bins, so a constant guesser scored 0.5
on both probe families — ≈0.308 run-mean, exactly the published `reset_lossy`
`R(k=12)`. A coin flip was indistinguishable from the rung described as partial
retention. RB-16 widened the task to 16 attributes/bins, dropping analytic chance
to `1/16 = 0.0625` per probe (`0.0357` as a run-mean over the default schedule).

## Deterministic, but a single draw

The answer for a prompt is a pure function of `(seed, prompt)` — BLAKE2b over
both, modulo the vocabulary size. So the SUT is reproducible, answers every arm
of the sweep identically (which is what makes its `R(k)` flat), and needs no RNG
state to carry across a hard reset. Because it is one fixed draw rather than an
expectation, the *measured* score is a sample near, not exactly at, analytic
chance; `docs/reference-ladder.md` reports both.

## Band behaviour: EXCLUDED, by construction

`P`, `C` and every `R(k)` are the same number here, so the learnable band
`C - P` is zero and the gain-curve driver marks the band **EXCLUDED** —
normalised retention is undefined for a system with nothing to retain. That is
the correct reading. This rung's job is to place the *raw* `R(k)` chance line so
the other rungs can be read as above or below chance.

## Knobs

- `RANDOM_GUESS_SEED` — int (default `0`); chooses which draw.
- `RANDOM_GUESS_NUM_ATTRIBUTES` — int in `[2, 20]` (default `16`); must match the
  task's `num_attributes` so the guess is uniform over exactly the vocabulary in
  play.

Both fail loud on a bad value rather than silently falling back to the default.

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m random_guess.clbench_main" \
  --extra-pythonpath suts/random_guess \
  --reset-every 1 --reset-every 2 --name random-guess-chance
```

Expected shape: `P == C == R(k)` at the chance line, band excluded.
