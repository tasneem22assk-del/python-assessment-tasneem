def calculate_total (subtotal, distance_km, premium=False):

    if type(subtotal) != float and type (subtotal) != int :
        raise ValueError("Subtotal must be number ")

    if type(distance_km) != float and type (distance_km) != int :
        raise ValueError("distance_km must be number ")
    if distance_km < 0 :
        raise ValueError("Distance_km must be greater than 0")
    if  type (premium) != bool:
        raise ValueError("Premium must be boolean ")
    if premium == True or subtotal >= 500:
        delivery=0

        print ("Delivery is free ")

    else :
        delivery = 30
        if distance_km >= 5 :
            delivery =  delivery + 10
        total=delivery+subtotal
        return  round (total)
if __name__ == "__main__":
        calculate_total(100, 3, False)
        calculate_total(450, 6, False)
        calculate_total(550, 6, False)
        calculate_total(100, 6, True)



