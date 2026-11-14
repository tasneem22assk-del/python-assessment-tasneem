def summarize_tickets( tickets):

    priority={
       "HIGH": 0 ,
      "MEDIUM": 0 ,
      "LOW": 0
}
    assignees =[]
    status = ['(OPEN','IN_PROGRESS','RESOLVED']
    seen_ids = []
    unresolved_ids = []
    for tickets  in  tickets:

        if "id" not in tickets or  "priority" not in tickets or "assignee" not in tickets  or "status" not in tickets or "tickets_id" not in tickets :
            raise ValueError("Tickets is missing a key ")
        tickets_id = tickets['id']
        if  type (tickets_id) != int :
            seen_ids.append(tickets_id)

        tickets_priority=(tickets['priority']).upper()
        tickets_status=(tickets['status']).upper()

        if  tickets_priority not in priority:
            raise ValueError("invalid priority")
        if  tickets_status not in status:
            raise ValueError("invalid status")
        priority[tickets_priority ] = priority[tickets_priority]+1

        assignee = tickets['assignee']
        if assignee is not None and assignee not in assignees :
            assignee.append(assignee)
        if tickets_status!= "RESOLVED":
            unresolved_ids.append(tickets_id)
    return {
        "counts_by_priority": priority[tickets_priority],
        "assignee": sorted(assignees),
        "unresolved":sorted (unresolved_ids)}

if   __name__ ==  "__main__":
                tickets = \
                   [{"id": 2,"priority":"high","status":"open","assignee":"Ali"},
                    {"id": 1,"priority":"LOW","status":"resolved","assignee":None},
                    {"id": 3,"priority":"high","status":"in_progress","assignee":"Ali"}]
                print (tickets)