"""Synthetic order-confirmation emails in the shape api.services.gmail._parse_message returns.

Modelled on the plain-text bodies of real DoorDash / Uber Eats / Grubhub /
Amazon / Walmart receipts. All names, numbers and addresses are made up.
"""

DOORDASH = {
    "id": "msg-doordash-1",
    "from": "DoorDash <no-reply@doordash.com>",
    "subject": "Your order from Chipotle Mexican Grill is confirmed",
    "date": "Sat, 21 Mar 2026 19:42:10 -0700",
    "snippet": "Thanks for your order! Your order from Chipotle Mexican Grill is on its way.",
    "body": (
        "Thanks for your order, Sam!\n"
        "Order from Chipotle Mexican Grill - Estimated arrival 8:05 PM\n"
        "Order #DD-7F3K92QX\n"
        "March 21, 2026\n"
        "1x Chicken Burrito Bowl $11.45\n"
        "2x Chips & Guacamole $4.95\n"
        "1x Mexican Coca-Cola $3.25\n"
        "Subtotal: $24.60\n"
        "Delivery fee: $2.99\n"
        "Tip: $4.00\n"
        "Order Total: $33.87\n"
        "Delivery to 360 Huntington Ave, Boston, MA\n"
    ),
}

UBER_EATS = {
    "id": "msg-ubereats-1",
    "from": "Uber Receipts <noreply@uber.com>",
    "subject": "Your Thursday evening order with Uber Eats",
    "date": "Thu, 26 Mar 2026 20:11:00 -0400",
    "snippet": "Here's your receipt for Panda Express.",
    "body": (
        "Your receipt\n"
        "Here's your order from Panda Express - Thanks for ordering\n"
        "Order # UE-55821930\n"
        "1x Orange Chicken Bowl $9.80\n"
        "1x Chow Mein $5.20\n"
        "Service fee $2.10\n"
        "Total: $17.10\n"
    ),
}

GRUBHUB = {
    "id": "msg-grubhub-1",
    "from": "Grubhub <orders@eat.grubhub.com>",
    "subject": "Your order from Sweetgreen has been placed",
    "date": "",
    "snippet": "Order placed. Sweetgreen is preparing your food.",
    "body": (
        "Order placed!\n"
        "Your order from Sweetgreen | Back Bay\n"
        "Order #GH-1180442\n"
        "03/18/2026\n"
        "Harvest Bowl - $14.95\n"
        "Kale Caesar - $12.45\n"
        "Tax - $1.71\n"
        "Total: $29.11\n"
    ),
}

AMAZON = {
    "id": "msg-amazon-1",
    "from": "Amazon.com <auto-confirm@amazon.com>",
    "subject": "Your Amazon.com order #112-4839201-7765432",
    "date": "Mon, 16 Mar 2026 09:03:44 +0000",
    "snippet": "Thanks for your order. We'll send a confirmation when your items ship.",
    "body": (
        "Hello Sam,\n"
        "Thank you for shopping with us. Your order has been placed.\n"
        "Order #112-4839201-7765432\n"
        "Placed on March 16, 2026\n"
        "1x Anker USB C Charger 65W $35.99\n"
        "2x AmazonBasics AA Batteries 24 Pack $13.49\n"
        "Item Subtotal: $62.97\n"
        "Estimated tax: $3.94\n"
        "Order Total: $66.91\n"
    ),
}

AMAZON_SHIPPED = {
    "id": "msg-amazon-2",
    "from": "Amazon.com <shipment-tracking@amazon.com>",
    "subject": "Your Amazon.com order of \"Sony WH-1000XM5...\" has shipped!",
    "date": "Wed, 25 Mar 2026 14:20:00 +0000",
    "snippet": "Your package is on the way.",
    "body": (
        "Your package has shipped and is on the way.\n"
        "Order #113-0042817-5521098\n"
        "Sony WH-1000XM5 Wireless Headphones - $328.00\n"
        "Order Total: $328.00\n"
        "Track your package at amazon.com/gp/your-account/order-history\n"
    ),
}

WALMART = {
    "id": "msg-walmart-1",
    "from": "Walmart.com <help@walmart.com>",
    "subject": "Thanks for your order",
    "date": "Tue, 10 Mar 2026 11:00:00 -0500",
    "snippet": "Your order #2000131-44590 is confirmed.",
    "body": (
        "We got your order!\n"
        "Order # 2000131-44590\n"
        "2026-03-10\n"
        "1x Great Value Whole Milk 1 Gallon $3.68\n"
        "1x Bananas 3 lb $1.62\n"
        "Order total: $5.30\n"
    ),
}

NEWSLETTER = {
    "id": "msg-news-1",
    "from": "Amazon.com <store-news@amazon.com>",
    "subject": "Deals picked for you",
    "date": "Fri, 20 Mar 2026 08:00:00 +0000",
    "snippet": "Save up to 40% on headphones this week.",
    "body": "Top deals this week. Save up to 40% on headphones and smart home devices.",
}

ALL_ORDERS = [DOORDASH, UBER_EATS, GRUBHUB, AMAZON, AMAZON_SHIPPED, WALMART]
