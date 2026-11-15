def test_start_without_assign():
    t =  Ticket(1, "VPN access", "HIGH")
    with pytest.raises(ValueError):
        t.start()