# Amenities

Canonical amenity keys. This file is generated from `skills/house-search/scripts/housesearch/vocab.py`, which is the source of truth; `scripts/check_repo.py` fails if they drift. Regenerate with `python3 scripts/check_repo.py --write-amenities`.

Use these keys in `requirements.json` and in each listing's `amenities` / `amenities_absent`. Portals use many spellings; the third column lists the phrases the helper recognises, and you should map other wording by judgement.

Default must-haves (deal-breakers unless the person says otherwise): `parking_2w`, `parking_4w`, `pets_allowed`.

Not amenity keys, because they are fields: property age (`age_years`), area (`area_sqft`), floor, bathrooms, main-door facing (`facing`), furnishing, rent. Intent such as "lake view" goes in `notes`.

## Parking

| Key | Label | Recognised phrases |
|---|---|---|
| `parking_2w` | 2-wheeler parking | 2 wheeler parking, two wheeler parking, 2wheeler parking, bike parking, scooter parking, 2w parking, 2 wheeler |
| `parking_4w` | 4-wheeler parking | 4 wheeler parking, four wheeler parking, 4wheeler parking, car parking, covered parking, 4w parking, 4 wheeler, parking |

## Safety and society

| Key | Label | Recognised phrases |
|---|---|---|
| `cctv` | CCTV camera security | cctv camera security, cctv cameras, cctv |
| `entrance_lobby` | Entrance lobby | entrance lobby, lobby |
| `gated_community` | Gated community | gated community, gated society, gated |
| `intercom` | Intercom facilities | intercom facilities, intercom |
| `lift` | Lift | lift, elevator |
| `power_backup` | 24/7 power backup | 24/7 power backup, 24x7 power backup, power backup, dg backup, generator backup, inverter backup |
| `security_24x7` | 24x7 security | 24x7 security, 24/7 security, 24 x 7 security, round the clock security, security guard, security |

## Utilities

| Key | Label | Recognised phrases |
|---|---|---|
| `paved_compound` | Paved compound | paved compound |
| `rain_water_harvesting` | Rain water harvesting | rain water harvesting, rainwater harvesting, rwh |
| `sewage_treatment_plant` | Sewage treatment plant | sewage treatment plant, sewage treatment, stp |
| `water_treatment_plant` | Water treatment plant | water treatment plant, water treatment, wtp |

## Recreation

| Key | Label | Recognised phrases |
|---|---|---|
| `amphitheatre` | Amphitheatre | amphitheatre, amphitheater |
| `childrens_play_area` | Children's play area | children's play area, childrens play area, kids play area, kids' play area, play area |
| `club_house` | Club house | club house, clubhouse |
| `gym` | Gymnasium | gymnasium, gym, fitness centre, fitness center |
| `indoor_games` | Indoor games | indoor games |
| `jogging_track` | Jogging track | jogging track, running track, jogging |
| `landscape_garden` | Landscape garden | landscape garden, landscaped garden, garden |
| `multipurpose_hall` | Multipurpose hall | multipurpose hall, multi purpose hall |
| `open_space` | Open space | open space |
| `park` | Park | park |
| `party_lawn` | Party lawn | party lawn |
| `reflexology_park` | Reflexology park | reflexology park, reflexology |
| `senior_citizen_sitout` | Senior citizen sit-out | senior citizen sit out, senior citizen sitout, senior citizen |
| `sit_out_area` | Sit-out area | sit out area, sitout area, sit out, sitout |
| `swimming_pool` | Swimming pool | swimming pool, pool |
| `theatre` | Theatre | mini theatre, home theatre, theatre, theater |
| `yoga_meditation` | Yoga / meditation area | yoga meditation area, yoga area, meditation area, yoga, meditation |

## Sports

| Key | Label | Recognised phrases |
|---|---|---|
| `badminton_court` | Badminton court | badminton court, badminton |
| `basketball_court` | Basketball court | basketball court, basketball |
| `cricket_pitch` | Cricket pitch | cricket pitch, cricket |
| `multipurpose_court` | Multipurpose court | multipurpose court, multi purpose court |
| `skating_rink` | Skating rink | skating rink, skating |
| `tennis_court` | Tennis court | tennis court, tennis |

## Household policies and features

| Key | Label | Recognised phrases |
|---|---|---|
| `pets_allowed` | Pets allowed | pet friendly, pets allowed, pet allowed, pets ok, pets |
| `vastu_compliant` | Vastu compliant | vastu compliant, vastu complaint, vastu |
