# Sources

Where to look for rentals. Defaults are for India; the structure (portals, managed rentals, community channels, civic and map data) carries over to other countries with different names. Platforms change names, filters and access rules often, so treat this list as a starting point and verify a source is live before you rely on it.

## How to use a source

1. Open the source's own search page once and set the filters by hand (city, locality, BHK, furnishing, property type, budget). Read the resulting URL to learn its current parameters. Do not reuse remembered URLs.
2. If you only have search: `site:<domain> <unit> <furnishing> <locality> rent`.
3. Record per source: `status` (`ok`, `empty`, `blocked`, `app_only`), `count`, and a note.

## Portals (search all of these first)

| Source | Domain | Good for |
|---|---|---|
| NoBroker | nobroker.in | Owner-direct, no-brokerage listings; strong in metros |
| MagicBricks | magicbricks.com | Largest volume; broker and owner |
| 99acres | 99acres.com | Large volume; verified-owner filters |
| Housing.com | housing.com | Gated-society listings with amenity detail |
| Square Yards | squareyards.com | Newer builds, managed listings |
| CommonFloor | commonfloor.com | Society-level pages |
| Makaan | makaan.com | Additional broker inventory |
| Quikr Homes / OLX | quikr.com, olx.in | Budget and owner-direct; quality varies, check carefully for scams |

## Managed and furnished rentals

For furnished, semi-furnished, serviced and "move-in ready" requests: NestAway, Zolo, Colive, Stanza Living and similar managed-rental brands, plus serviced-apartment operators. These usually quote an all-in monthly price (rent plus services); normalise and note it.

## Community channels

Neighbourhood and city rental groups (Facebook groups, Reddit city communities, Telegram and WhatsApp-style groups that publish openly), and society resident forums. Useful for pet-friendly, bachelor-friendly and off-market homes. Often unstructured and not de-duplicated; treat details as claims to verify and never repost a person's contact details.

## Maps and civic data (for checks, not listings)

| Need | Source |
|---|---|
| Geocoding, directions, traffic | Google Maps (Geocoding and Routes APIs with a key; Maps web for manual fallback) |
| Hospitals, malls, metro, police | OpenStreetMap via Overpass (`hs.py nearby`); Google Maps for verification |
| Police jurisdiction and crime figures | City or state police websites, open-data portals, NCRB for city-level context |
| Waterlogging | Local news, municipal corporation and disaster-management bulletins, traffic-police rain advisories |

## Apps

Mobile apps for these platforms have no URL you can open. Their listings are usually also on the web version; use that. For app-only inventory, tell the person which app and which filters to use, and do not pretend you searched it.

## Scams and quality signals

Flag, do not hide: rent far below market for the area; request for advance before a viewing; photos reused across several listings; "owner abroad" stories; listing with no society or street. Say why you are wary.

## Adding a source

Add a row here and nothing else. The skill reads this file at run time; there is no code to change. Include the domain, what it is good for, and any known access limits.
