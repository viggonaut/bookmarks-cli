# X Auth

X bookmark access requires a user access token, not app-only bearer auth.

## Required X app setup

In the X Developer Console:

1. Create or select an App under a Project
2. Enable OAuth 2.0
3. Add a redirect URI that matches your local config
4. Use a public client / PKCE flow
5. Ensure these scopes are allowed:
   - `bookmark.read`
   - `tweet.read`
   - `users.read`
   - `offline.access`

## Local config

Set these in your local `.env`:

```bash
X_CLIENT_ID=<your-x-client-id>
X_REDIRECT_URI=http://127.0.0.1:8741/callback
X_OAUTH_SCOPES=bookmark.read tweet.read users.read offline.access
```

## Login flow

Run:

```bash
python3 -m bookmarks_cli auth x-login
```

That command:

1. Starts a temporary local callback server on the port in `X_REDIRECT_URI`
2. Prints the X authorization URL
3. Waits for you to complete login in the browser
4. Exchanges the code for tokens
5. Fetches your authenticated X user info
6. Stores the token state in:
   - `_meta/state/x_oauth.json`

## After login

Run the onboarding import:

```bash
python3 -m bookmarks_cli backfill x-bookmarks
```

Then use incremental sync:

```bash
python3 -m bookmarks_cli sync x-bookmarks
```
