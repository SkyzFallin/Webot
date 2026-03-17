# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability

If you discover a security issue in this project, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, contact the maintainer directly:

- **Email**: security@wescastle.com
- **GitHub**: [@SkyzFallin](https://github.com/SkyzFallin)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You can expect an initial response within **48 hours**.

## Security Considerations

This project handles **financial API credentials** and **trading operations**. Users should:

- **Never** commit `.env` files or credentials to version control
- Use a dedicated Webull account for bot trading
- Start with **paper trading mode** before going live
- Restrict file permissions on config files containing credentials (`chmod 600`)
- Run the bot in an isolated environment (VM, container, or dedicated host)
- Review all code changes before deploying to live trading
- Monitor bot activity and set conservative risk limits

## Credential Handling

- All credentials are loaded from environment variables or `.env` files
- No credentials are hardcoded in source
- The `.env.example` file contains only placeholder values
- `.gitignore` should always exclude `.env` and any credential files

## Disclaimer

This software is provided as-is for educational and personal use. The maintainer is not responsible for financial losses resulting from the use of this bot.
