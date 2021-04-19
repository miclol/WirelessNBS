from collections import defaultdict
from copy import deepcopy
from json import JSONDecodeError, load
from math import ceil, floor, log2
from os import mkdir, name, system
from pathlib import Path
from pynbs import read
from re import sub
from shutil import make_archive, rmtree

def returnNBS(song):
    notes = defaultdict(list)
    for tick in song:
        for note in tick[1]:
            tick, key, instrument = note.tick, note.key - 33, instruments[note.instrument]
            if key < 0:
                exit(f"Note on tick {tick} too low for Minecraft.")
            elif key > 24:
                exit(f"Note on tick {tick} too high for Minecraft.")
            elif note.instrument > 15:
                exit(f"Invalid instrument on tick {tick}.")
            else:
                notes[tick] += [[note.instrument, key]]
                instrument[2] += 1
        for instrument in instruments.values():
            if instrument[2] > instrument[1]:
                instrument[1] = instrument[2]
            instrument[2] = 0
    print(f"Instruments needed for {file}:")
    for instrument in instruments.values():
        instrument.pop()
        if instrument[1] > 0:
            print(f"{instrument[0]} needed: {instrument[1]}")
    return notes

def returnConfig():
    try:
        neededCoords, instrumentCoords = 0, {}
        config = load(open(f"{Path(file).stem}.json"))
        if "obstructions" in config:
            obstructions = [tuple(coords) for coords in config["obstructions"]]
        else:
            obstructions = None
        for instrument in instruments.values():
            instrumentName, instrumentCount = instrument
            instrumentJSON = instrumentName.lower()
            neededCoords += instrumentCount
            if instrumentJSON in config["instruments"]:
                instrumentCoords[instrumentName] = [tuple(coords) for coords in config["instruments"][instrumentJSON]]
                if len(instrumentCoords[instrumentName]) != instrumentCount:
                    exit(f"{instrumentName} needs {instrumentCount} coordinates, not "
                         f"{len(instrumentCoords[instrumentName])}.")
                else:
                    neededCoords -= instrumentCount
        if neededCoords != 0 or not all(len(i) == 3 for instrument in instrumentCoords.values() for i in instrument):
            exit("Please view documentation to create a proper config file.")
        instrumentCoords = {k: value for key, value in instrumentCoords.items() for k, v in instruments.items()
                            if v[0] == key}
        return instrumentCoords, obstructions
    except FileNotFoundError:
        exit("Please view documentation on how to create a config file.")
    except JSONDecodeError:
        exit("Malformed JSON File.")

def returnPlacement(instrumentCoords, obstructions):  # Thx for Lawrenc3X for helping me with this.
    def badNoteblockPlacement(x, y, z):               # (https://github.com/Lawrenc3X)
        yield x, y - 1, z
        yield x, y + 1, z
        yield x, y + 2, z

    def badOverlap(x, y, z):
        for y in (y - 1, y + 1):
            yield x, y, z + 1
            yield x + 1, y, z
            yield x, y, z - 1
            yield x - 1, y, z

    def orthogonal(x, y, z):
        yield x, y, z + 1
        yield x + 1, y, z
        yield x, y, z - 1
        yield x - 1, y, z

    def placement(x, y, z):
        orthX, orthY, orthZ = x, y, z
        if obstructions:
            if (x, y, z) in obstructions:
                exit("Obstructing Block is blocking Note Block placement.")
            for coords in noteblockCoords:
                for (x, y, z) in badNoteblockPlacement(coords[0], coords[1], coords[2]):
                    if (x, y, z) in obstructions and (x, y, z) != (coords[0], coords[1] + 2, coords[2]):
                        exit("Obstructing Block is blocking Note Block from playing.")
        for p in orthogonal(orthX, orthY, orthZ):
            if p not in hazards:
                return p
        return None

    noteblockCoords = [c for coords in instrumentCoords.values() for c in coords]
    hazards = noteblockCoords.copy()
    if obstructions:
        hazards.extend(obstructions)

    for coordsX, coordsY, coordsZ in noteblockCoords:
        for coords in badNoteblockPlacement(coordsX, coordsY, coordsZ):
            if coords in noteblockCoords:
                exit("Invalid Noteblock Placement and/or Obstructing Block is blocking Redstone placement.")
            if coords != (coordsX, coordsY + 2, coordsZ):
                hazards.append(coords)

        hazards.extend(badOverlap(coordsX, coordsY, coordsZ))

    neighbours = defaultdict(int)
    for coordsX, coordsY, coordsZ in noteblockCoords:
        for coords in orthogonal(coordsX, coordsY, coordsZ):
            neighbours[coords] += 1

    hazards.extend(p for p in neighbours if neighbours[p] >= 2)

    redstoneCoords = defaultdict(list)
    for coordsX, coordsY, coordsZ in noteblockCoords:
        coords = placement(coordsX, coordsY, coordsZ)
        if coords:
            for instrument in instruments.values():
                if instrument[1] > 0:
                    redstoneCoords[instrument[0]] += [coords]
                    instrument[1] -= 1
                    break
        else:
            exit("Invalid Noteblock Placement and/or Obstructing Block is blocking Redstone placement.")
    redstoneCoords = {k: value for key, value in redstoneCoords.items() for k, v in instruments.items() if v[0] == key}
    return redstoneCoords

def clear():
    if name == "nt":
        system("cls")
    else:
        system("clear")

def main(song):
    if Path(song).suffix != ".nbs":
        exit("File isn't .nbs. Perhaps you spelt it wrong?")
    try:
        song = read(song)
    except FileNotFoundError:
        exit("File Does Not Exist. Perhaps you spelt it wrong?")
    except:
        exit("Invalid .nbs File.")

    notes = returnNBS(song)
    noteblockCoords, obstructions = returnConfig()
    redstoneCoords = returnPlacement(noteblockCoords, obstructions)
    tagName = "note_" + functionName[:9].lower()
    tagTName = tagName + "_t"
    tempoMultiplier = 20 / song.header.tempo
    noteC = 0
    tickCount = round(song.header.song_length * tempoMultiplier)
    power = ceil(log2(tickCount))
    rep = 2

    clear()
    mkdir(functionName)
    mkdir(f"{functionName}/data")
    mkdir(f"{functionName}/data/minecraft")
    mkdir(f"{functionName}/data/minecraft/tags")
    mkdir(f"{functionName}/data/minecraft/tags/functions")
    mkdir(f"{functionName}/data/{functionName.lower()}")
    mkdir(f"{functionName}/data/{functionName.lower()}/functions")
    mkdir(f"{functionName}/data/{functionName.lower()}/functions/ticks")
    mkdir(f"{functionName}/data/{functionName.lower()}/functions/tree")

    with open(f"{functionName}/pack.mcmeta", 'w') as f:
        f.write("{\n\t\"pack\": {\n\t\t\"pack_format\": 1,\n\t\t\"description\": \"From NBS File To Wireless Noteblocks"
                " Made by miclol.\"\n\t}\n}")
        f.close()

    with open(f"{functionName}/data/minecraft/tags/functions/tick.json", 'w') as f:
        f.write("{\"values\": [\"%s:tick\"]}" % functionName.lower())
        f.close()

    with open(f"{functionName}/data/minecraft/tags/functions/load.json", 'w') as f:
        f.write("{\"values\": [\"%s:load\"]}" % functionName.lower())
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/load.mcfunction", 'w') as f:
        f.write(f"scoreboard objectives add {tagName} dummy\nscoreboard objectives add {tagTName} dummy\ntellraw @a "
                f"{{\"text\":\"{file} Ready!\",\"color\":\"green\"}}")
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/tick.mcfunction", 'w') as f:
        f.write(f"execute as @a[tag={tagName}] at @s run scoreboard players add @s {tagName} 1\nexecute as "
                f"@a[tag={tagName}] at @s run function {functionName.lower()}:tree/0_{2 ** power - 1}")
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/play.mcfunction", 'w') as f:
        f.write(f"execute as @a[distance=..32] run tag @s add {tagName}\nexecute as @a[distance=..32] run scoreboard "
                f"players set @s {tagTName} -1")
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/pause.mcfunction", 'w') as f:
        f.write(f"execute as @a[tag={tagName}] run tag @s remove {tagName}")
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/stop.mcfunction", 'w') as f:
        f.write(f"execute as @a[tag={tagName}] run scoreboard players reset @s {tagName}\nexecute as @a[tag={tagName}] "
                f"run scoreboard players reset @s {tagTName}\nexecute as @a[tag={tagName}] run tag @s remove {tagName}")
        f.close()

    with open(f"{functionName}/data/{functionName.lower()}/functions/uninstall.mcfunction", 'w') as f:
        f.write(f"tag @a remove {tagName}\nscoreboard players remove @a {tagName}\nscoreboard players remove @a "
                f"{tagTName}\ndatapack disable \"file/{functionName}.zip\"\ntellraw @a "
                f"[\"\",{{\"text\":\"{functionName}\",\"underlined\":true,\"color\":\"gold\"}},{{\"text\":\" Noteblocks"
                f" Uninstalled. You may now remove it from your data pack folder.\",\"color\":\"yellow\"}}]")
        f.close()

    for p in range(power, 0, -1):
        num = 0
        for _ in range(rep):
            upNum = 2 ** p - 1 + num
            avgNum = (num + upNum) / 2
            print(f"Building Tree: {num}-{upNum}")
            if p > 1:
                with open(f"{functionName}/data/{functionName.lower()}/functions/tree/{num}_{upNum}.mcfunction",
                          'w') as f:
                    f.write(f"execute as @a[scores={{{tagName}={num}..{2 ** p + 1 + num}}}] run function "
                            f"{functionName.lower()}:tree/{num}_{floor(avgNum)}\nexecute as @a"
                            f"[scores={{{tagName}={ceil(avgNum)}..{2 ** p + 1 + ceil(avgNum)}}}] run "
                            f"function {functionName.lower()}:tree/{ceil(avgNum)}_{upNum}")
                    f.close()
            else:
                with open(f"{functionName}/data/{functionName.lower()}/functions/tree/{num}_{upNum}.mcfunction",
                          'w') as f:
                    f.write(f"execute as @a[scores={{{tagName}={num}..{2 ** p + 1 + num},{tagTName}=..{num - 1}}}] run "
                            f"function {functionName.lower()}:ticks/{num}")
                    if upNum <= tickCount:
                        f.write(f"\nexecute as @a[scores={{{tagName}={ceil(avgNum)}..{2 ** p + 1 + ceil(avgNum)},"
                                f"{tagTName}=..{upNum - 1}}}] run function {functionName.lower()}:ticks/{upNum}")
                    f.close()
            num += 2 ** p
            if num > tickCount:
                break
        rep *= 2

    for tick in range(int(tickCount + 1)):
        print(f"Creating Tick: {tick}/{int(tickCount)}")
        with open(f"{functionName}/data/{functionName.lower()}/functions/ticks/{tick}.mcfunction", 'w') as f:
            f.write(f"scoreboard players set @s {tagTName} {tick}")
            if tick == tickCount:
                f.write(f"\nfunction {functionName.lower()}:stop")
            f.close()

    for tick, note in notes.items():
        noteC += 1
        print(f"Creating Note: {noteC}/{len(notes.keys())}")
        tempNoteblockCoords, tempRedstoneCoords = deepcopy(noteblockCoords), deepcopy(redstoneCoords)
        with open(f"{functionName}/data/{functionName.lower()}/functions/ticks/"
                  f"{round(tick * tempoMultiplier)}.mcfunction", 'a') as f:
            for n in note:
                noteblock, redstone = tempNoteblockCoords[n[0]][0], tempRedstoneCoords[n[0]][0]
                f.write(f"\nsetblock {noteblock[0]} {noteblock[1]} {noteblock[2]} "
                        f"note_block[note={n[1]}]\nsetblock {redstone[0]} {redstone[1]} {redstone[2]} "
                        f"redstone_block\nsetblock {redstone[0]} {redstone[1]} {redstone[2]} air")
                tempNoteblockCoords[n[0]].pop(0), tempRedstoneCoords[n[0]].pop(0)
            f.close()

    print("Making it Into a Zip File...")
    make_archive(functionName, "zip", functionName)
    rmtree(functionName, True)
    print("Done!")


if __name__ == "__main__":
    instruments = {0: ["Piano", 0, 0], 1: ["Double Bass", 0, 0], 2: ["Bass Drum", 0, 0], 3: ["Snare Drum", 0, 0],
                   4: ["Click", 0, 0], 5: ["Guitar", 0, 0], 6: ["Flute", 0, 0], 7: ["Bell", 0, 0], 8: ["Chime", 0, 0],
                   9: ["Xylophone", 0, 0], 10: ["Iron Xylophone", 0, 0], 11: ["Cow Bell", 0, 0],
                   12: ["Didgeridoo", 0, 0], 13: ["Bit", 0, 0], 14: ["Banjo", 0, 0], 15: ["Pling", 0, 0]}
    file = input("Input .nbs File: ")
    functionName = sub(r"[^a-zA-Z]", '', input("Enter Function Name: "))
    clear()
    main(file)
