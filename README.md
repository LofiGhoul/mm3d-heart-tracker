# Heart Piece Tracker (Majora's Mask 3D)

A small GTK4/libadwaita app that reads a Majora's Mask 3D save slot and shows
which of the 52 Pieces of Heart you have and which you still need, grouped by region
with a hint for each.

## Run

    python3 heart_tracker.py [path/to/save0.bin]

or `./install.sh` once to add it to your app launcher (and `mm3d-heart-tracker` to `~/.local/bin`).

- **Open** (Ctrl+O) a `save0.bin` / `save1.bin` / `save2.bin`, or drop one on the window.
  Slot files dumped with Checkpoint/JKSM or taken from Citra/Azahar/Lime3DS both work.
- If the other slots sit in the same folder, they show up as tabs.
- **All / Missing** filters the list.
- The window reloads by itself when the save file changes, so you can keep it open
  next to an emulator. Ctrl+R reloads by hand.
- It remembers the last file you opened. On first run it looks in emulator folders
  and `~/Downloads`.

Needs only Python 3 with PyGObject, GTK 4 and libadwaita ≥ 1.7. It reads the save and never writes to it.

## How it decides

- 51 pieces are read straight from the game's own flags (event flags, scene
  collectible flags, chest flags).
- **Stock Pot Inn toilet hand:** MM3D clears this flag on every Song of Time, so it
  can't be read from the save. The app works out how many pieces you have from your
  hearts (max hearts − 3 starting − boss containers, ×4, + pieces toward the next heart).
  If that's one more than the flags account for, the hand is marked **Inferred**.
- MM3D swapped two rewards from the N64 version: Dampé's dig gives the heart piece and
  Koume's boat archery gives a bottle. The list follows MM3D.
- The two Termina Field grotto chests (Peahat and Dodongo) use flags that can't be
  told apart, so they show as "#1" and "#2".

`mm3d_save.py` also works from the command line: `python3 mm3d_save.py save0.bin`.
