"""NPC tasks. Each guide teaches an idea, then offers a short task. Completing
it unlocks a species-specific third move for any eligible Mintling you carry:
  budgeting task (PoketMart shopkeeper) -> Coincub learns Rainy Day
  repayment task (banking guide)        -> Tabbit learns Due Date (practical PocketBank task)
  security task (security guide)        -> Guardillo learns Lockdown
"""
from ..data.moves import MOVES
from ..data.species import SPECIES
from ..data.world import TASK_TOPIC


def task_species(task):
    return [(sid, sp) for sid, sp in SPECIES.items() if tuple(sp["unlock"]) == ("task", task)]


def teach_task_moves(state, task):
    """Teach the task's move to eligible party Mintlings. Returns the lines to show."""
    lines = []
    for mon in state.party:
        sp = mon.species
        if tuple(sp["unlock"]) == ("task", task) and sp["third"] not in mon.moves:
            if mon.offer_move(sp["third"])[0] == "learned":
                lines.append(f"{mon.name} learned {MOVES[sp['third']]['name']}!")
    return lines


def reward_hint(task):
    names = [f"a {sp['name']} the move {MOVES[sp['third']]['name']}" for _, sp in task_species(task)]
    return f"Complete it and I can teach {' or '.join(names)}." if names else ""


def later_hint(task):
    names = [f"a {sp['name']}, bring it to me and I'll teach it {MOVES[sp['third']]['name']}"
             for _, sp in task_species(task)]
    return f"If you have {' or '.join(names)}." if names else ""


def run_npc_task(game, npc, done=None):
    st = game.state
    task = npc["task"]
    flag = f"task:{task}"
    speaker = npc["name"]

    def finish(*_):
        if done:
            done()

    def completed():
        st.flags.add(flag)
        game.audio.play("level")
        taught = teach_task_moves(st, task)
        extra = [] if taught else [later_hint(task)]
        game.say(npc["task_done"] + taught + extra, speaker=speaker, then=finish)

    if flag in st.flags:
        taught = teach_task_moves(st, task)
        if taught:
            game.audio.play("level")
        game.say(npc["lines"] + taught, speaker=speaker, then=finish)
        return

    def start(yes):
        if not yes:
            game.say(["No problem. Come back whenever you like."], speaker=speaker, then=finish)
            return
        if task == "repayment":
            from .bank import GuidedBankScene
            game.push(GuidedBankScene(game, on_close=lambda ok: completed() if ok else finish(),
                                      title="Banking Guide Cora's task"))
            return
        from .common import QuestionScene

        def answered(correct):
            if correct:
                completed()
            else:
                game.say(["Not quite, but now you know why. Have another go any time!"], speaker=speaker,
                         then=finish)

        game.push(QuestionScene(game, game.quiz.draw(TASK_TOPIC[task], 2), f"{speaker}'s task", answered,
                                on_cancel=finish))

    intro = npc["lines"] + npc["task_intro"]
    hint = reward_hint(task)
    if hint:
        intro = intro + [hint]
    game.say(intro, speaker=speaker,
             then=lambda: game.ask("Try the task?", [("Yes, let's try", True), ("Not now", False)], start,
                                   speaker=speaker))
