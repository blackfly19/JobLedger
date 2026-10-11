# JobLedger

A privacy-first job-application tracker that runs a local LLM on your own machine. It reads your Gmail, figures out which messages are job-application related, keeps a structured record of them, and lets you ask questions about your applications in plain English. No email content ever leaves your device.

## Why

Job searching generates a lot of scattered email: confirmations, rejections, recruiter replies, interview invites. Tracking it by hand is tedious. The obvious fix is to point an LLM at your inbox, but doing that through a hosted API means handing your personal email to a third party. JobLedger does the whole thing locally instead, using a quantized Qwen3-8B model running on Apple Silicon via MLX, so the convenience of an LLM comes without giving up the privacy of your inbox.

## What it does

- **Reads Gmail safely.** Connects through OAuth with a read-only scope, so the app can never modify or send mail. It extracts and cleans message bodies, handling both multipart and HTML emails.
- **Classifies locally.** A locally hosted Qwen3-8B model decides which emails are job-application related and pulls out the relevant details. Everything runs on-device.
- **Keeps a structured record.** Extracted data is validated against a schema and stored in a local SQLite database, your application ledger.
- **Answers questions.** A tool-calling agent lets you ask things like "which companies haven't responded in three weeks" in natural language, and answers them against your tracked data.

## How it works

**The ingestion pipeline.** Emails are fetched read-only, cleaned, and passed to the local model for classification and extraction. The model's output is never trusted blindly: it is validated against a Pydantic schema, normalised to smooth over small model quirks, and retried automatically when it returns invalid JSON. Treating the model's output as untrusted input is central to keeping the data reliable.

**The query agent.** Natural-language questions are handled by a hand-written agent loop running over the local model server. The design deliberately keeps the model on a short leash:

- The agent only has access to **read-only tracker tools**, so it can look things up but never change your data.
- **Date calculations are done in code, not by the model**, because small models are unreliable at arithmetic and date logic. The model decides what to ask for; the code computes the answer.
- The loop has **step limits** to prevent runaway behaviour, and feeds **errors back to the model** so it can correct a bad tool call rather than failing silently.

The theme throughout is using the model for what it is good at (understanding messy language) and keeping code in charge of anything that needs to be correct.

## Tech stack

Python, MLX, Qwen3-8B, Gmail API, Pydantic, SQLite.

## Status

Working: Gmail ingestion, local classification and extraction, structured storage, and the question-answering agent. Still evolving.
