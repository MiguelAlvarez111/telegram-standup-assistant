#!/usr/bin/env python3
import argparse
from pathlib import Path


def html_list(items):
    return '<ul>\n' + '\n'.join(f'        <li>{item}</li>' for item in items) + '\n      </ul>'


def html_participants(blocks):
    out = []
    for name, bullets in blocks:
        out.append(f'      <h3 style="margin-bottom: 6px;">{name}</h3>')
        out.append('      <ul>')
        for bullet in bullets:
            out.append(f'        <li>{bullet}</li>')
        out.append('      </ul>')
    return '\n'.join(out)


def html_actions_table(actions):
    rows = [
        '      <table style="border-collapse: collapse; width: 100%; margin-top: 12px;">',
        '        <tr>',
        '          <th style="border:1px solid #d0d7de; background:#f6f8fa; text-align:left; padding:10px;">Qué</th>',
        '          <th style="border:1px solid #d0d7de; background:#f6f8fa; text-align:left; padding:10px;">Quién</th>',
        '        </tr>',
    ]
    for task, owner in actions:
        rows.extend([
            '        <tr>',
            f'          <td style="border:1px solid #d0d7de; padding:10px;">{task}</td>',
            f'          <td style="border:1px solid #d0d7de; padding:10px;">{owner}</td>',
            '        </tr>',
        ])
    rows.append('      </table>')
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--from-header', required=True)
    parser.add_argument('--to-header', required=True)
    parser.add_argument('--participants', required=True)
    parser.add_argument('--general-summary', required=True)
    parser.add_argument('--participant-block', action='append', default=[])
    parser.add_argument('--key-point', action='append', default=[])
    parser.add_argument('--action', action='append', default=[])
    args = parser.parse_args()

    participant_blocks = []
    for block in args.participant_block:
        name, bullets = block.split('::', 1)
        participant_blocks.append((name, [b.strip() for b in bullets.split('||') if b.strip()]))

    actions = []
    for action in args.action:
        task, owner = action.split('::', 1)
        actions.append((task.strip(), owner.strip()))

    template = Path(args.template).read_text()
    plain_participant_summary = '\n'.join(
        f"- {name}: {' '.join(bullets)}" for name, bullets in participant_blocks
    )
    plain_key_points = '\n'.join(f'- {kp}' for kp in args.key_point)
    plain_actions = '\n'.join(f'- {task} — Responsable: {owner}.' for task, owner in actions)

    rendered = template
    rendered = rendered.replace('From: Your Name <you@example.com>', args.from_header)
    rendered = rendered.replace('To: you@example.com', args.to_header)
    rendered = rendered.replace('{{DATE}}', args.date)
    rendered = rendered.replace('{{PARTICIPANTS}}', args.participants)
    rendered = rendered.replace('{{GENERAL_SUMMARY}}', args.general_summary)
    rendered = rendered.replace('{{PLAIN_PARTICIPANT_SUMMARY}}', plain_participant_summary)
    rendered = rendered.replace('{{PLAIN_KEY_POINTS}}', plain_key_points)
    rendered = rendered.replace('{{PLAIN_ACTIONS}}', plain_actions)
    rendered = rendered.replace('{{HTML_PARTICIPANT_SUMMARY}}', html_participants(participant_blocks))
    rendered = rendered.replace('{{HTML_KEY_POINTS}}', html_list(args.key_point))
    rendered = rendered.replace('{{HTML_ACTIONS_TABLE}}', html_actions_table(actions))

    Path(args.output).write_text(rendered)
    print(args.output)


if __name__ == '__main__':
    main()
