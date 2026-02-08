# Sample Outputs (Real)
Generated at: `2026-02-08T20:20:38+00:00`

Window: `2026-02-08T20:20:38+00:00` → `2026-02-09T20:20:38+00:00` (gs_id=1)

> Note: Results depend on your DB contents (TLEs + generated passes).

## /passes
Request:

`http://127.0.0.1:8000/passes?gs_id=1&start=2026-02-08T20%3A20%3A38%2B00%3A00&end=2026-02-09T20%3A20%3A38%2B00%3A00&limit=50`

Response:

```json`
{
  "count": 26,
  "items": [
    {
      "id": 9334,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T20:34:46.109995+00:00",
      "end_ts": "2026-02-08T21:14:37.184496+00:00",
      "duration_s": 2391,
      "max_elev_deg": 62.61625655181765
    },
    {
      "id": 6996,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T21:00:22.561123+00:00",
      "end_ts": "2026-02-08T21:07:35.459082+00:00",
      "duration_s": 433,
      "max_elev_deg": 2.4322276894662727
    },
    {
      "id": 13974,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T21:29:10.130478+00:00",
      "end_ts": "2026-02-08T21:46:56.272908+00:00",
      "duration_s": 1066,
      "max_elev_deg": 35.50228506374911
    },
    {
      "id": 9335,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T23:16:19.438281+00:00",
      "end_ts": "2026-02-08T23:49:16.590488+00:00",
      "duration_s": 1977,
      "max_elev_deg": 19.985561376956788
    },
    {
      "id": 13975,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T23:17:01.647482+00:00",
      "end_ts": "2026-02-08T23:33:34.793907+00:00",
      "duration_s": 993,
      "max_elev_deg": 24.44881193053486
    },
    {
      "id": 11619,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T03:36:55.853704+00:00",
      "end_ts": "2026-02-09T03:55:39.526263+00:00",
      "duration_s": 1124,
      "max_elev_deg": 48.960131493978274
    },
    {
      "id": 6997,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T05:12:41.725179+00:00",
      "end_ts": "2026-02-09T05:25:30.105409+00:00",
      "duration_s": 768,
      "max_elev_deg": 9.807318422926711
    },
    {
      "id": 4696,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T05:16:12.615862+00:00",
      "end_ts": "2026-02-09T05:29:59.209637+00:00",
      "duration_s": 827,
      "max_elev_deg": 14.76478089913862
    },
    {
      "id": 11620,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T05:25:33.624922+00:00",
      "end_ts": "2026-02-09T05:41:34.833270+00:00",
      "duration_s": 961,
      "max_elev_deg": 18.832129194203645
    },
    {
      "id": 6998,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T06:55:18.384863+00:00",
      "end_ts": "2026-02-09T07:13:42.645762+00:00",
      "duration_s": 1104,
      "max_elev_deg": 78.31014062175055
    },
    {
      "id": 4697,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T06:58:30.450927+00:00",
      "end_ts": "2026-02-09T07:15:28.212732+00:00",
      "duration_s": 1018,
      "max_elev_deg": 49.53351842855353
    },
    {
      "id": 6999,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T08:46:05.075491+00:00",
      "end_ts": "2026-02-09T08:56:25.664304+00:00",
      "duration_s": 621,
      "max_elev_deg": 5.178291949415679
    },
    {
      "id": 13976,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T09:23:55.827375+00:00",
      "end_ts": "2026-02-09T09:41:37.771298+00:00",
      "duration_s": 1062,
      "max_elev_deg": 33.56965881696534
    },
    {
      "id": 9336,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T10:14:19.255469+00:00",
      "end_ts": "2026-02-09T10:52:39.341295+00:00",
      "duration_s": 2300,
      "max_elev_deg": 45.371625926873605
    },
    {
      "id": 13977,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T11:11:33.309862+00:00",
      "end_ts": "2026-02-09T11:28:52.370824+00:00",
      "duration_s": 1039,
      "max_elev_deg": 26.789050691580726
    },
    {
      "id": 9337,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T12:51:38.113082+00:00",
      "end_ts": "2026-02-09T13:32:04.794731+00:00",
      "duration_s": 2427,
      "max_elev_deg": 82.41835408587876
    },
    {
      "id": 11621,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T13:54:26.415280+00:00",
      "end_ts": "2026-02-09T13:56:56.885826+00:00",
      "duration_s": 150,
      "max_elev_deg": 0.2381956633873653
    },
    {
      "id": 9338,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T15:31:59.837536+00:00",
      "end_ts": "2026-02-09T16:12:10.209618+00:00",
      "duration_s": 2410,
      "max_elev_deg": 59.21333962200504
    },
    {
      "id": 11622,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T15:32:29.591641+00:00",
      "end_ts": "2026-02-09T15:51:25.056444+00:00",
      "duration_s": 1135,
      "max_elev_deg": 46.579868984545946
    },
    {
      "id": 4698,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T16:29:19.023337+00:00",
      "end_ts": "2026-02-09T16:29:36.029703+00:00",
      "duration_s": 17,
      "max_elev_deg": 0.0031419834768667593
    },
    {
      "id": 11623,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T17:21:18.713021+00:00",
      "end_ts": "2026-02-09T17:38:14.093412+00:00",
      "duration_s": 1015,
      "max_elev_deg": 20.403679918768102
    },
    {
      "id": 4699,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T18:05:58.158414+00:00",
      "end_ts": "2026-02-09T18:23:14.001246+00:00",
      "duration_s": 1036,
      "max_elev_deg": 51.237408776565346
    },
    {
      "id": 9339,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T18:12:14.845056+00:00",
      "end_ts": "2026-02-09T18:52:49.703234+00:00",
      "duration_s": 2435,
      "max_elev_deg": 76.783514045916
    },
    {
      "id": 7000,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T18:14:47.009586+00:00",
      "end_ts": "2026-02-09T18:32:37.249603+00:00",
      "duration_s": 1070,
      "max_elev_deg": 45.414483036321776
    },
    {
      "id": 4700,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T19:51:26.213642+00:00",
      "end_ts": "2026-02-09T20:05:31.935198+00:00",
      "duration_s": 846,
      "max_elev_deg": 15.310422083392345
    },
    {
      "id": 7001,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T20:01:46.589936+00:00",
      "end_ts": "2026-02-09T20:17:07.869028+00:00",
      "duration_s": 921,
      "max_elev_deg": 18.649269248930363
    }
  ]
}
```

## /schedule/best
Request:

`http://127.0.0.1:8000/schedule/best?gs_id=1&start=2026-02-08T20%3A20%3A38%2B00%3A00&end=2026-02-09T20%3A20%3A38%2B00%3A00&metric=duration`

Response:

```json
{
  "gs_id": 1,
  "satellite_id": null,
  "start": "2026-02-08T20:20:38+00:00",
  "end": "2026-02-09T20:20:38+00:00",
  "metric": "duration",
  "score": 23783.0,
  "count": 18,
  "passes": [
    {
      "id": 9334,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T20:34:46.109995+00:00",
      "end_ts": "2026-02-08T21:14:37.184496+00:00",
      "duration_s": 2391,
      "max_elev_deg": 62.61625655181765
    },
    {
      "id": 13974,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T21:29:10.130478+00:00",
      "end_ts": "2026-02-08T21:46:56.272908+00:00",
      "duration_s": 1066,
      "max_elev_deg": 35.50228506374911
    },
    {
      "id": 9335,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-08T23:16:19.438281+00:00",
      "end_ts": "2026-02-08T23:49:16.590488+00:00",
      "duration_s": 1977,
      "max_elev_deg": 19.985561376956788
    },
    {
      "id": 11619,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T03:36:55.853704+00:00",
      "end_ts": "2026-02-09T03:55:39.526263+00:00",
      "duration_s": 1123,
      "max_elev_deg": 48.960131493978274
    },
    {
      "id": 6997,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T05:12:41.725179+00:00",
      "end_ts": "2026-02-09T05:25:30.105409+00:00",
      "duration_s": 768,
      "max_elev_deg": 9.807318422926711
    },
    {
      "id": 11620,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T05:25:33.624922+00:00",
      "end_ts": "2026-02-09T05:41:34.833270+00:00",
      "duration_s": 961,
      "max_elev_deg": 18.832129194203645
    },
    {
      "id": 6998,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T06:55:18.384863+00:00",
      "end_ts": "2026-02-09T07:13:42.645762+00:00",
      "duration_s": 1104,
      "max_elev_deg": 78.31014062175055
    },
    {
      "id": 6999,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T08:46:05.075491+00:00",
      "end_ts": "2026-02-09T08:56:25.664304+00:00",
      "duration_s": 620,
      "max_elev_deg": 5.178291949415679
    },
    {
      "id": 13976,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T09:23:55.827375+00:00",
      "end_ts": "2026-02-09T09:41:37.771298+00:00",
      "duration_s": 1061,
      "max_elev_deg": 33.56965881696534
    },
    {
      "id": 9336,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T10:14:19.255469+00:00",
      "end_ts": "2026-02-09T10:52:39.341295+00:00",
      "duration_s": 2300,
      "max_elev_deg": 45.371625926873605
    },
    {
      "id": 13977,
      "satellite_id": 5,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T11:11:33.309862+00:00",
      "end_ts": "2026-02-09T11:28:52.370824+00:00",
      "duration_s": 1039,
      "max_elev_deg": 26.789050691580726
    },
    {
      "id": 9337,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T12:51:38.113082+00:00",
      "end_ts": "2026-02-09T13:32:04.794731+00:00",
      "duration_s": 2426,
      "max_elev_deg": 82.41835408587876
    },
    {
      "id": 11621,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T13:54:26.415280+00:00",
      "end_ts": "2026-02-09T13:56:56.885826+00:00",
      "duration_s": 150,
      "max_elev_deg": 0.2381956633873653
    },
    {
      "id": 9338,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T15:31:59.837536+00:00",
      "end_ts": "2026-02-09T16:12:10.209618+00:00",
      "duration_s": 2410,
      "max_elev_deg": 59.21333962200504
    },
    {
      "id": 4698,
      "satellite_id": 1,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T16:29:19.023337+00:00",
      "end_ts": "2026-02-09T16:29:36.029703+00:00",
      "duration_s": 17,
      "max_elev_deg": 0.0031419834768667593
    },
    {
      "id": 11623,
      "satellite_id": 4,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T17:21:18.713021+00:00",
      "end_ts": "2026-02-09T17:38:14.093412+00:00",
      "duration_s": 1015,
      "max_elev_deg": 20.403679918768102
    },
    {
      "id": 9339,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T18:12:14.845056+00:00",
      "end_ts": "2026-02-09T18:52:49.703234+00:00",
      "duration_s": 2434,
      "max_elev_deg": 76.783514045916
    },
    {
      "id": 7001,
      "satellite_id": 2,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T20:01:46.589936+00:00",
      "end_ts": "2026-02-09T20:17:07.869028+00:00",
      "duration_s": 921,
      "max_elev_deg": 18.649269248930363
    }
  ]
}
```

## /schedule/top
Request:

`http://127.0.0.1:8000/schedule/top?gs_id=1&start=2026-02-08T20%3A20%3A38%2B00%3A00&end=2026-02-09T20%3A20%3A38%2B00%3A00&metric=duration&k=3`

Response:

```json
{
  "gs_id": 1,
  "satellite_id": null,
  "start": "2026-02-08T20:20:38+00:00",
  "end": "2026-02-09T20:20:38+00:00",
  "metric": "duration",
  "k": 3,
  "count": 3,
  "passes": [
    {
      "id": 9339,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T18:12:14.845056+00:00",
      "end_ts": "2026-02-09T18:52:49.703234+00:00",
      "duration_s": 2434,
      "max_elev_deg": 76.783514045916
    },
    {
      "id": 9337,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T12:51:38.113082+00:00",
      "end_ts": "2026-02-09T13:32:04.794731+00:00",
      "duration_s": 2426,
      "max_elev_deg": 82.41835408587876
    },
    {
      "id": 9338,
      "satellite_id": 3,
      "ground_station_id": 1,
      "start_ts": "2026-02-09T15:31:59.837536+00:00",
      "end_ts": "2026-02-09T16:12:10.209618+00:00",
      "duration_s": 2410,
      "max_elev_deg": 59.21333962200504
    }
  ]
}
```
