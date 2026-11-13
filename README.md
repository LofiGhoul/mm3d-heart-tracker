# MM3D 100% Tracker

A GTK4/libadwaita app for Linux that reads a Majora's Mask 3D save slot and shows
how close you are to 100%. You get an overall completion percentage and a checklist per category:

| Category | What's tracked |
|---|---|
| Pieces of Heart | All 52, by region, with step-by-step instructions for each |
| Masks | All 24 |
| Songs | The 10 songs |
| Items | 15 inventory items and the Bombers' Notebook |
| Bottles | All 7 (MM3D adds Gorman's Mystery Milk) |
| Upgrades | Quivers, bomb bags, wallets, Razor/Gilded Sword, Mirror Shield |
| Great Fairies | The 5 Great Fairy rewards, with this cycle's stray fairy count |
| Spider Houses | Both rewards, with this cycle's Gold Skulltula count |
| Bosses | 4 remains and 4 boss Heart Containers |
| Owl Statues | All 10 |

## Run

    python3 heart_tracker.py [path/to/save0.bin]

or `./install.sh` once to add it to your app launcher (and `mm3d-heart-tracker` to `~/.local/bin`).

- **Open** (Ctrl+O) a `save0.bin` / `save1.bin` / `save2.bin`, or drop one on the window.
  Slot files dumped with Checkpoint/JKSM or taken from Citra/Azahar/Lime3DS both work.
- If the other slots sit in the same folder, they show up as tabs.
- Tap a category to open its checklist. **All / Missing** filters it.
- In Pieces of Heart, tap a piece to expand step-by-step instructions (written for the 3DS version).
- The window reloads by itself when the save file changes, so you can keep it open
  next to an emulator. Ctrl+R reloads by hand.
- It remembers the last file you opened. On first run it looks in emulator folders
  and `~/Downloads`.

Needs only Python 3 with PyGObject, GTK 4 and libadwaita ≥ 1.7. It reads the save and never writes to it.

## Mask icons (optional, bring your own)

No game artwork ships with this app. If you have your own mask icons, put them in either
`icons/` next to `heart_tracker.py` (git ignores this folder) or
`~/.local/share/mm3d-heart-tracker/icons/`. The Masks page then shows a grid of all 24,
with the ones you're missing faded, and each row gets its icon.

Name each file after the mask (`.png`, `.svg`, `.webp` or `.jpg`):

    deku  goron  zora  fierce  truth  kafei  allnight  bunny  keaton  garo  romani  troupe
    postman  couple  greatfairy  gibdo  dongero  kamaro  captain  stone  bremen  blast  scents  giant

For example `icons/deku.png` or `icons/allnight.png`. Any you don't provide just show without an icon.
The same naming works for other checks too: drop the prefix from the check id in `checklist.py`
(`i_hookshot` → `hookshot.png`).

## How it decides

- Everything is read straight from the save: event flags, scene flags, the inventory,
  mask and bottle slots, upgrade and quest bitfields, and owl statue flags.
- **Stock Pot Inn toilet hand:** MM3D clears this flag on every Song of Time, so it
  can't be read from the save. The app works out how many pieces you have from your
  hearts (max hearts − 3 starting − boss containers, ×4, + pieces toward the next heart).
  If that's one more than the flags account for, the hand is marked **Inferred**.
- MM3D swapped two rewards from the N64 version: Dampé's dig gives the heart piece and
  Koume's boat archery gives a bottle. The lists follow MM3D.
- Stray fairy and Gold Skulltula counts reset every cycle, so those sections track the
  permanent rewards. The counts are shown as progress.
- The overall percentage counts each check once, even when it appears in two sections
  (for example, the Mask of Truth is under both Masks and Spider Houses).
- Not tracked: Bomber's Notebook entries and fishing.

`mm3d_save.py` also works from the command line: `python3 mm3d_save.py save0.bin`.
Piece instructions live in `guide.py`, and the other checklists in `checklist.py`.
