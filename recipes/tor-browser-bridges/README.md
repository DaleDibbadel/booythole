# Tor Browser: automatic built-in bridges (Kasm file mapping)

Kasm's stock Tor Browser image cannot reach Tor relays directly on some networks (bootstrap stalls at 5%). Tor Browser's own profile preference file `user.js` selects the built-in obfs4 bridges:

```
user_pref("torbrowser.settings.bridges.enabled", true);
user_pref("torbrowser.settings.bridges.source", 0);
user_pref("torbrowser.settings.bridges.builtin_type", "obfs4");
user_pref("extensions.torlauncher.quickstart", true);
user_pref("torbrowser.settings.quickstart.enabled", true);
user_pref("extensions.torlauncher.prompt_at_startup", false);
```

Kasm file mapping (Admin > Workspaces > the Tor Browser workspace > File Mapping) with destination
`/home/kasm-default-profile/tor-browser/tor-browser/Browser/TorBrowser/Data/Browser/profile.default/user.js`.
The destination must be inside the image's default-profile template, **not** `/home/kasm-user/...`: a mapping under `/home/kasm-user/tor-browser` pre-creates that directory and the image then skips copying its own Tor Browser into the home directory (`start-tor-browser: No such file or directory`).
Verified in a disposable Kasm session: the browser bootstraps by itself and `check.torproject.org/api/ip` reports `IsTor:true`.
