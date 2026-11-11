SELECT complaint_type,
       count(*) AS requests,
       count(closed_at) AS closed_requests,
       round(median(epoch(closed_at - created_at) / 3600), 2) AS median_hours_to_close
FROM requests
GROUP BY complaint_type
ORDER BY requests DESC, complaint_type;
