#!/usr/bin/env python3
import argparse
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path


def parse_mml_parts(mml_text: str):
    subject_match = re.search(r'^Subject:\s*(.+)$', mml_text, re.MULTILINE)
    subject = subject_match.group(1).strip() if subject_match else 'Standup Diario'

    body = mml_text.split('\n\n', 1)[1] if '\n\n' in mml_text else mml_text
    html_marker = '<#part type=text/html>'
    multipart_marker = '<#multipart type=alternative>'
    end_marker = '<#/multipart>'

    plain = body
    html = None

    if multipart_marker in body and html_marker in body:
        after_multi = body.split(multipart_marker, 1)[1]
        plain = after_multi.split(html_marker, 1)[0]
        html = after_multi.split(html_marker, 1)[1]
        html = html.split(end_marker, 1)[0].strip()
        plain = plain.replace(multipart_marker, '').replace(end_marker, '').strip()
    else:
        plain = body.strip()

    return subject, plain.strip(), html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mml', required=True)
    parser.add_argument('--gmail-user', required=True)
    parser.add_argument('--gmail-app-password', required=True)
    parser.add_argument('--to', required=True)
    parser.add_argument('--subject')
    parser.add_argument('--from-name', default='Miguel Alvarez')
    args = parser.parse_args()

    text = Path(args.mml).read_text()
    parsed_subject, plain_body, html_body = parse_mml_parts(text)
    subject = args.subject or parsed_subject

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f'{args.from_name} <{args.gmail_user}>'
    msg['To'] = args.to
    msg.set_content(plain_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as s:
        s.starttls()
        s.login(args.gmail_user, args.gmail_app_password)
        s.send_message(msg)

    print('SMTP_SENT')


if __name__ == '__main__':
    main()
