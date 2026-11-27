# Development corpus

Practice mail for building and tuning LayerSight. This is not the official 20-email test set, and it must not be used as if it were.

36 messages: 24 phishing, 12 genuine. Each scoring rule in `engineering.md` section 4 has at least one message, listed in `coverage.yaml`. Five genuine messages are hard negatives (a password reset, a newsletter that uses a shortener, a real PDF invoice, an urgent internal IT notice, a shipping update). Three phishing messages are hard positives (a compromised company mailbox whose authentication passes, a wire-transfer request with no link and no attachment, and a `paypal.com.secure-login.io` link).

`labels.csv` is the only place the label lives. File names describe the case for people reading the corpus. The classifier must not read the file name or this label.

Attachments are described by name and type. `27-genuine-pdf-invoice.eml` is the one MIME message with an attachment part; its payload is the four characters `%PDF` and is not a document. Analysis code must ignore attachment payloads anyway.

The two files in `configs/` are the canonical untrained and trained layer configurations. They differ only in `user_training.level`.
