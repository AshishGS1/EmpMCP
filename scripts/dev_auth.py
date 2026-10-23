"""Developer helper for the self-signed JWT setup.

    python scripts/dev_auth.py keygen
        Writes keys/private.pem and keys/public.pem (RSA 2048). Point
        AUTH_PUBLIC_KEY_PATH at the public one.

    python scripts/dev_auth.py mint --sub alice --scopes employees:read,departments:read
    python scripts/dev_auth.py mint --sub bob --scopes all --ttl 300
        Prints a signed token on stdout (details go to stderr), so it works in
        TOKEN=$(python scripts/dev_auth.py mint ...)

In production your FastAPI service mints the tokens (it alone holds the private key);
this script just lets you exercise the server by hand. Issuer and audience default to
AUTH_ISSUER / AUTH_AUDIENCE from the environment or .env.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import dotenv_values
from joserfc import jwt
from joserfc.jwk import RSAKey

ALL_SCOPES = ["employees:read", "departments:read", "salary:read"]


def keygen(args: argparse.Namespace) -> None:
    key_dir = Path(args.dir)
    private_path = key_dir / "private.pem"
    public_path = key_dir / "public.pem"
    if private_path.exists() and not args.force:
        sys.exit(f"{private_path} already exists (use --force to overwrite)")

    key_dir.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Wrote {private_path} (keep secret: only the token minter needs it)")
    print(f"Wrote {public_path} (set AUTH_PUBLIC_KEY_PATH to this)")


def mint(args: argparse.Namespace) -> None:
    env = {**dotenv_values(".env"), **os.environ}
    issuer = args.issuer or env.get("AUTH_ISSUER")
    audience = args.audience or env.get("AUTH_AUDIENCE")
    if not issuer or not audience:
        sys.exit("Set AUTH_ISSUER and AUTH_AUDIENCE in .env, or pass --issuer/--audience")

    scopes = ALL_SCOPES if args.scopes == ["all"] else args.scopes
    now = int(time.time())
    claims = {
        "iss": issuer,
        "aud": audience,
        "sub": args.sub,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": now + args.ttl,
    }
    if args.jti:
        claims["jti"] = args.jti
    try:
        key = RSAKey.import_key(Path(args.key).read_bytes())
    except OSError as exc:
        sys.exit(f"Cannot read private key {args.key}: {exc.strerror} (run keygen first)")

    print(jwt.encode({"alg": "RS256", "typ": "JWT"}, claims, key))
    print(
        f"# sub={args.sub} scopes={' '.join(scopes)} expires in {args.ttl}s",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    gen = commands.add_parser("keygen", help="generate an RSA key pair")
    gen.add_argument("--dir", default="keys")
    gen.add_argument("--force", action="store_true")
    gen.set_defaults(func=keygen)

    mn = commands.add_parser("mint", help="print a signed token")
    mn.add_argument("--sub", required=True, help="user the token is for")
    mn.add_argument(
        "--scopes",
        required=True,
        type=lambda text: text.replace(",", " ").split(),
        help="comma-separated scopes, or 'all'",
    )
    mn.add_argument("--ttl", type=int, default=900, help="lifetime in seconds")
    mn.add_argument("--jti", help="optional id to correlate logs (FastAPI sends its request id)")
    mn.add_argument("--key", default="keys/private.pem")
    mn.add_argument("--issuer")
    mn.add_argument("--audience")
    mn.set_defaults(func=mint)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()