import click
import pykka
import random
from time import sleep
from .words import names, said, utterances
import logging


class Utterance:
    def __init__(self, speaker, text):
        self.speaker = speaker
        self.text = text


class ControlMessage:
    def __init__(self, cmd, sender=None, data=None):
        self.cmd = cmd
        self.sender = sender
        self.data = data


class Coordinator(pykka.ThreadingActor):
    def __init__(self):
        super().__init__()
        self.lines = []

    def on_receive(self, msg):
        if msg.cmd == 'pprint':
            output = []
            for line in self.lines:
                output.append(line)
                output.append('\n\n')
            return ''.join(output)
        elif msg.cmd == 'add':
            self.lines.append(msg.data)
        elif msg.cmd == 'begin':
            characters = pykka.ActorRegistry.get_by_class(Character)
            # concoct a first utterance
            speaker = random.choice(characters)
            recipient = random.choice([c for c in characters if c != speaker])
            recipient.tell(Utterance(speaker, 'Hello, world!'))
        return None


class Character(pykka.ThreadingActor):
    def __init__(self, name, coordinator):
        super().__init__()
        self.name = name
        self.coordinator = coordinator

    def on_receive(self, message):
        # optionally respond to sender
        if random.random() < 0.8:
            utterance = Utterance(self.actor_ref, random.choice(utterances))
            self.coordinator.tell(frame(utterance, self.name))
            message.speaker.tell(utterance)

        # optionally say something to someone else
        if random.random() < 0.3:
            characters = pykka.ActorRegistry.get_by_class(Character)
            recipient = random.choice([
                c for c in characters if c != message.speaker and c != self
            ])
            utterance = Utterance(self.actor_ref, random.choice(utterances))  # noqa
            self.coordinator.tell(frame(utterance, self.name))
            recipient.tell(utterance)


@click.command()
@click.option('--seconds', default=0.15)
@click.option('--debug/--no-debug', default=False)
def run(seconds, debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    coordinator = Coordinator.start()

    _ = [
        Character(name=c, coordinator=coordinator).start(
            name=c, coordinator=coordinator
        )
        for c in names
    ]

    _ = coordinator.ask(ControlMessage('begin'))

    sleep(seconds)

    response = coordinator.ask(ControlMessage('pprint'))

    click.echo(response)

    pykka.ActorRegistry.stop_all()


def frame(utterance, speaker_name):
    order = random.random()
    if order < 0.4:
        line = f'{speaker_name} {random.choice(said)}, "{utterance.text}"'
    elif order < 0.6:
        line = f'"{utterance.text[:-1]}," {speaker_name} {random.choice(said)}.'  # noqa
    else:
        line = f'"{utterance.text}"'
    return ControlMessage('add', data=line)
