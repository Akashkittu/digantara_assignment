from collections import defaultdict
from app.schedule.optimizer import weighted_interval_scheduling


def optimize_network(passes, metric="duration"):
    """
    passes: list of dict rows from DB (multiple ground stations)
    metric: duration | count | max_elev
    """

    # Group passes by ground station
    by_station = defaultdict(list)
    for p in passes:
        by_station[p["ground_station_id"]].append(p)

    network_schedule = []
    total_tracking_time = 0
    total_passes = 0
    unique_satellites = set()

    for gs_id, gs_passes in by_station.items():

        scheduled = weighted_interval_scheduling(gs_passes, metric)

        for p in scheduled:
            network_schedule.append(p)
            total_passes += 1
            total_tracking_time += p["duration_s"]
            unique_satellites.add(p["satellite_id"])

    return {
        "total_passes": total_passes,
        "total_tracking_time_s": total_tracking_time,
        "unique_satellites_tracked": len(unique_satellites),
        "schedule": network_schedule,
    }
