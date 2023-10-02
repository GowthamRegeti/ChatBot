from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import db_helper
import geneic_helper

app = FastAPI()


@app.get("/")
async def get_root():
    return JSONResponse(content={"message": "This is a GET request."})


@app.post("/")
async def handle_request(request: Request):
    # Retrieve the JSON data from the request
    payload = await request.json()
    # Extract the necessary infor
    # based on the structure of the WebhookRequest from DialogfLow
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    session_id = geneic_helper.extract_session_id(output_contexts[0]["name"])
    intent_handler_dict = {
        "new.order": new_order,
        "order.add - context: ongoing-order": add_to_order,
        "order.complete - context: ongoing-order": complete_order,
        "order.remove - context: ongoing-order": remove_from_order,
        "track.order": track,
        'track.order - context: ongoing-tracking': track_order,
    }
    return intent_handler_dict[intent](parameters, session_id)


inProgress_dict = {}


def new_order(parameters: dict, session_id: str):
    if session_id in inProgress_dict:
        del inProgress_dict[session_id]
        return JSONResponse(content={
            "fulfillmentText": "Your previous session was deleted. starting a new order. You can say things like \"I "
                               "want two pizzas and one mango lassi\". Make sure to specify a quantity for every food "
                               "item! Also, we have only the following items on our menu: Pav Bhaji, Chole Bhature, "
                               "Pizza, Mango Lassi, Masala Dosa, Biryani, Vada Pav, Rava Dosa, and Samosa."})


def add_to_order(parameters: dict, session_id: str):
    food_items = parameters['food-item']
    quantities = parameters['number']
    if len(food_items) != len(quantities):
        fulfillment_text = f"Sorry I didn't understand. Please specify the food items and quantity clearly?"
    else:
        new_food_dict = dict(zip(food_items, quantities))
        if session_id in inProgress_dict:
            current_food_dict = inProgress_dict[session_id]
            current_food_dict = {key: current_food_dict.get(key, 0) + new_food_dict.get(key, 0) for key in
                                 set(current_food_dict) | set(new_food_dict)}
            inProgress_dict[session_id] = current_food_dict
        else:
            inProgress_dict[session_id] = new_food_dict

        order_text = geneic_helper.get_text_from_food_dict(inProgress_dict[session_id])

        fulfillment_text = f"So far you have : {order_text} \ndo you need anything else?"
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inProgress_dict:
        return JSONResponse(
            content={"fulfillmentText": "I'm having trouble in finding your order. Sorry can you place new order?"})
    current_order = inProgress_dict[session_id]
    food_items = parameters['food-item']
    removed_item = []
    no_such_items = []
    for item in food_items:
        if item not in food_items:
            no_such_items.append(item)
        else:
            removed_item.append(item)
            del current_order[item]
    if len(removed_item) > 0:
        fulfillment_text = f"Removed {','.join(removed_item)} from your order\n"
    if len(no_such_items) > 0:
        fulfillment_text += f"your current order doesn't exists {','.join(no_such_items)}\n"
    if len(current_order) == 0:
        fulfillment_text += f"your order is empty"
    else:
        order_str = geneic_helper.get_text_from_food_dict(current_order)
        fulfillment_text += f"Here is what is left in your order {order_str}"
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def complete_order(parameters: dict, session_id: str):
    if session_id not in inProgress_dict:
        fulfillment_text = "I'm having trouble in placing your order.Sorry! can you place a new order?"
    else:
        order = inProgress_dict[session_id]
        order_id = save_order(order)
        if order_id == -1:
            fulfillment_text = "Sorry I couldn't place order due to backend error. " \
                               "Please place a new order again!!!"
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = "Awesome The order is placed." \
                               f"Here is order Id # {order_id}." \
                               f"Your order total is {order_total} which you can pay at the time of delivery."
        del inProgress_dict[session_id]
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def save_order(order: dict):
    next_order_id = db_helper.get_next_order_id()
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if rcode == -1:
            return -1

    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id


def track(parameters: dict, session_id: str):
    pass


def track_order(parameters: dict, session_id: str):
    order_id = int(parameters['order_id'])
    status = db_helper.get_order_status(order_id)
    if status:
        fulfillment_text = f"The status of order id {order_id} is {status}"
    else:
        fulfillment_text = f"No order found with this order id : {order_id}"
    return JSONResponse(content={"fulfillmentText": fulfillment_text})
