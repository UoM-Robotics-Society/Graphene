# Graphene 6 (aka G6)

## What's in this repository?

This is the main repository for Graphene 6, the 6th iteration of the Robot Orchestra conductor. The core conductor code lives within the `conductor` sub-directory. A number of instruments have been implemented as part of this, and live in the `instruments` directory. These make for some good examples when working on your own instruments. `lm-library` is a submodule to the libmusician library. It can be left un-cloned however it's nice to have everything together in one place when working on stuff :).

It is recommended to open `G6.code-workspace` to load all folders at once.

## Instruments

### GlockOBot

GlockOBot is implemented using a large distributed shift register. This is the most complete of all the examples, sporting the trifecta of notes, lighting, and control channels.

### Tambourine

Of this examples, this is by far the simplest to work with. There's a single servo, and it swings forwards as note E4 (64).

### Steppers

This example implements four stepper motors, cabable of playing any four notes simultaniously. While the stepper-driving is not especially interesting (it's just bit-banging) this example makes use of `"g6.h"` to access some g6-internal data. Specifically, it monitors `lm_g6_node_id` to identify if the instrument is connected to the conductor and ready to receive note information.

## Speed Glossary

|               |                                                                                            |
| ------------- | ------------------------------------------------------------------------------------------ |
| `G6`          | Shorthand for Graphene 6 but more commonly used for...                                     |
| `g6`          | ...the underlying communication protocol used by Graphene.                                 |
| `libmusician` | The C library exposed to instrument programmers for interfacing with the Conductor system. |
| `lm_`         | Abbreviation of `libmusician`. Prefixes all public function names.                         |
