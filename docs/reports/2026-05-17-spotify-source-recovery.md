# Spotify Source Recovery

Checked at: 2026-05-17T19:48:00Z

## Findings

- Spotify did work historically. The old `assistant` Postgres database has one
  Spotify account row with stored access and refresh token fields, plus 3,091
  listening records in `spotify_listening_records`.
- The historical listening watermark is `2026-02-15T15:09:00Z`; records span
  `2025-12-23T12:54:46Z` through `2026-02-15T15:09:00Z`.
- Folio has the original Spotify integration spec at
  `Areas/Tech/Paia/Development/specs/spotify-integration.md` and the
  Strava/Spotify plan at
  `Areas/Tech/Paia/Development/plans/2025-12-27-strava-spotify-integration.md`.
- Paia OS has a newer implementation under
  `/path/to/paia-os/src/paia/integrations/spotify`
  with `AsyncSpotifyClient`, OAuth helpers, `SpotifyAdapter`, and
  `SpotifySyncService`.
- Paia OS also has an hourly Spotify history worker at
  `/path/to/paia-os/src/paia/workers/spotify_sync.py`.
- Paia OS migration support exists at
  `/path/to/paia-os/scripts/migrate_music.py`.
- The `paia` Postgres database has Spotify credential rows and cached playlist
  metadata, but no `integration_events` rows for Spotify.

## Current Blocker

The live Spotify API path is not fresh. Refreshing the stored historical token
with the recovered historical app credentials returns `invalid_client`, and no
current Spotify client secret was found in the checked keychain/environment
locations. This points to rotated or mismatched Spotify app credentials, not a
missing implementation.

## State Decision

Promote `connector.personal.spotify` from "planned" to "declared stale
historical source" for Samantha. The agent-facing package may use the old
assistant Postgres listening cache as stale historical evidence, but must not
claim current Spotify freshness or live API access.

## Next Action

Restore the current Spotify app `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` that
matches the stored refresh token, or re-run OAuth against the current app. Then
run the Paia OS Spotify sync path, record a fresh b-state source watermark, and
rebuild Samantha's package.
