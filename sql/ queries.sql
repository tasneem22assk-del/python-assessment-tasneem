SELECT * FROM tickets  WHERE  assignee_id  <> 'RESOLVED' ORDER BY id ;
SELECT COALESCE (users.username, 'Unassigned') AS assignee count (*) unresolved_count;
SELECT priority count(tickets_id) ;
update tickets where status ='OPEN';