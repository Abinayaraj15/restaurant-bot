from flask import Flask, request, jsonify, render_template_string, session
from dotenv import load_dotenv
import os
from datetime import datetime
import re

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")


# --------------------------
# HELPER FUNCTION: Check meal time
# --------------------------
def check_time_valid(meal: str) -> bool:
    now = datetime.now().replace(second=0, microsecond=0).time()
    breakfast_start, breakfast_end = datetime.strptime("07:30", "%H:%M").time(), datetime.strptime("10:30", "%H:%M").time()
    lunch_start, lunch_end = datetime.strptime("12:00", "%H:%M").time(), datetime.strptime("14:00", "%H:%M").time()
    dinner_start, dinner_end = datetime.strptime("19:00", "%H:%M").time(), datetime.strptime("21:00", "%H:%M").time()
    
    if meal == "breakfast":
        return breakfast_start <= now <= breakfast_end
    elif meal == "lunch":
        return lunch_start <= now <= lunch_end
    elif meal == "dinner":
        return dinner_start <= now <= dinner_end
    return False

# --------------------------
# MENU ITEMS
# --------------------------
MENU_ITEMS = {
    # Breakfast
    "idli": "breakfast", "idli sambar": "breakfast", "dosa": "breakfast", "plain dosa": "breakfast",
    "masala dosa": "breakfast", "pongal": "breakfast", "upma": "breakfast",
    "appam with milk": "breakfast", "idiyappam with coconut milk": "breakfast",
    "vada": "breakfast", "poori with potato curry": "breakfast", "chapati with kurma": "breakfast",
    "milk": "breakfast", "coffee": "breakfast", "tea": "breakfast",

    # Lunch
    "sambar rice": "lunch", "rasam rice": "lunch", "lemon rice": "lunch", "curd rice": "lunch",
    "tamarind rice": "lunch", "kurma with chapati": "lunch",
    "chicken curry with rice": "lunch", "fish curry with rice": "lunch", "mutton biryani": "lunch",
    "veg thali": "lunch",

    # Dinner
    "idiyappam with coconut milk": "dinner", "chapati with dal curry": "dinner", "parotta with salna": "dinner",
    "onion dosa": "dinner", "uttapam": "dinner", "kichadi": "dinner", "veg noodles": "dinner",
    "chicken fried rice": "dinner", "mutton sukka with chapati": "dinner",
}

# --------------------------
# SIMPLE PLURALIZER
# --------------------------
def pluralize(word: str, quantity: int) -> str:
    irregulars = {
        "idli": "Idlis",
        "dosa": "Dosas",
        "vada": "Vadas",
        "parotta": "Parottas",
        "poori": "Pooris"
    }
    if quantity > 1:
        return irregulars.get(word.lower(), word.title() + "s")
    else:
        return word.title()

# --------------------------
# BOT LOGIC
# --------------------------
def restaurant_bot(query: str):
    try:
        query_lower = query.lower()
        orders = session.get("orders", [])

        # --- Handle order completion ---
        if query_lower in ["no", "nope", "nothing", "done", "that's all", "that is all"]:
            if orders:
                order_list = [f"{o['quantity']} {o['item']}" for o in orders]
                final_order = ", ".join(order_list)
                session.pop("orders", None)  # clear session after checkout
                return f"🙏 Thank you for your order! You ordered: {final_order}. Your food will be served soon."
            else:
                return "🙏 Thank you! No items were ordered."

        # --- Extract quantity (like "2 parottas") ---
        quantity = 1
        match = re.search(r"(\d+)\s+([a-zA-Z ]+)", query_lower)
        if match:
            quantity = int(match.group(1))
            item_text = match.group(2).strip()
        else:
            item_text = query_lower.strip()

        # --- Normalize plural input (parottas → parotta) ---
        if item_text.endswith("s") and item_text[:-1] in MENU_ITEMS:
            item_text = item_text[:-1]

        # --- Check if the user is ordering a dish ---
        for item, meal in MENU_ITEMS.items():
            if item in item_text:
                if check_time_valid(meal):
                    dish_name = pluralize(item, quantity)

                    # merge orders if item already exists
                    found = False
                    for o in orders:
                        if o["item"].lower() == dish_name.lower():
                            o["quantity"] += quantity
                            found = True
                            break
                    if not found:
                        orders.append({"item": dish_name, "quantity": quantity})

                    session["orders"] = orders
                    return f"✅ Added {quantity} {dish_name} to your order. Anything else?"
                else:
                    return f"⏰ {meal.title()} is served only at specific hours. Please check the menu."

        # --- Meal-specific queries ---
        if "breakfast" in query_lower:
            menu_text = "Idli & Sambar, Dosa, Pongal, Upma, Appam with Milk, Idiyappam with Coconut Milk, Vada, Poori with Potato Curry, Chapati with Kurma, Milk/Coffee/Tea."
            return f"✅ Breakfast available now: {menu_text}" if check_time_valid("breakfast") else f"⏰ Breakfast is served only between 7:30 AM – 10:30 AM.\nHere is the menu: {menu_text}"

        if "lunch" in query_lower:
            menu_text = "Sambar Rice, Rasam Rice, Lemon Rice, Curd Rice, Tamarind Rice, Kurma with Chapati, Chicken Curry with Rice, Fish Curry with Rice, Mutton Biryani, Veg Thali."
            return f"✅ Lunch available now: {menu_text}" if check_time_valid("lunch") else f"⏰ Lunch is served only between 12:00 PM – 2:00 PM.\nHere is the menu: {menu_text}"

        if "dinner" in query_lower:
            menu_text = "Idiyappam with Coconut Milk, Chapati with Dal Curry, Parotta with Salna, Onion Dosa, Uttapam, Kichadi, Veg Noodles, Chicken Fried Rice, Mutton Sukka with Chapati."
            return f"✅ Dinner available now: {menu_text}" if check_time_valid("dinner") else f"⏰ Dinner is served only between 7:00 PM – 9:00 PM.\nHere is the menu: {menu_text}"

        # --- Full menu ---
        if "menu" in query_lower:
            return (
                "📋 Full Tamil Food Menu:\n\n"
                "🍳 Breakfast: Idli & Sambar, Dosa, Pongal, Upma, Appam with Milk, Idiyappam with Coconut Milk, Vada, Poori with Potato Curry, Chapati with Kurma, Milk / Coffee / Tea\n\n"
                "🌿 Lunch: Sambar Rice, Rasam Rice, Lemon Rice, Curd Rice, Tamarind Rice, Kurma with Chapati, Chicken Curry with Rice, Fish Curry with Rice, Mutton Biryani, Veg Thali\n\n"
                "🌙 Dinner: Idiyappam with Coconut Milk, Chapati with Dal Curry, Parotta with Salna, Onion Dosa, Uttapam, Kichadi, Veg Noodles, Chicken Fried Rice, Mutton Sukka with Chapati"
            )

        # --- Fallback response ---
        return "Sorry!I’m here to help you with the restaurant menu.Please check our menu"

    except Exception as e:
        print("Error in restaurant_bot:", e)
        return "⚠️ Sorry, something went wrong. Please try again."

# --------------------------
# FLASK ROUTES
# --------------------------
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Spice Garden - Restaurant Bot</title>
      <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #f9f9f9; display: flex; justify-content: center;
        align-items: center; height: 100vh; margin: 0; }
        .chat-container { background: #fff; width: 420px; height: 600px;
        border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        display: flex; flex-direction: column; overflow: hidden; }
        .chat-header { background: #ff7043; color: white; text-align: center;
        padding: 15px; font-size: 20px; font-weight: bold; }
        .chat-box { flex: 1; padding: 15px; overflow-y: auto; background: #fafafa;
        display: flex; flex-direction: column; }
        .message { margin: 10px 0; padding: 10px 14px; border-radius: 18px;
        max-width: 80%; line-height: 1.4; word-wrap: break-word; }
        .user { background: #e3f2fd; align-self: flex-end; color: #0d47a1; border-top-right-radius: 0; }
        .bot { background: #f1f8e9; align-self: flex-start; color: #33691e; border-top-left-radius: 0; }
        .chat-input { display: flex; border-top: 1px solid #ddd; }
        .chat-input input { flex: 1; padding: 12px; border: none; outline: none; font-size: 14px; }
        .chat-input button { background: #ff7043; color: white; border: none;
        padding: 12px 20px; cursor: pointer; font-size: 14px;
        transition: background 0.3s; margin-left: 2px;}
        .chat-input button:hover { background: #f4511e; }
      </style>
    </head>
    <body>
      <div class="chat-container">
        <div class="chat-header">🍴 Spice Garden Bot</div>
        <div class="chat-box" id="chat"></div>
        <div class="chat-input">
          <input type="text" id="query" />
          <button onclick="sendMessage()">Send</button>
          <button onclick="startSpeechRecognition()">🎤 Speak</button>
        </div>
      </div>

      <script>
        async function sendMessage() {
          const queryInput = document.getElementById("query");
          const query = queryInput.value.trim();
          if (!query) return;

          const chatBox = document.getElementById("chat");
          chatBox.innerHTML += "<div class='message user'><b>You:</b> " + query + "</div>";
          queryInput.value = "";
          chatBox.scrollTop = chatBox.scrollHeight;

          try {
            const res = await fetch("/chat", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query })
            });
            const data = await res.json();
            chatBox.innerHTML += "<div class='message bot'><b>Bot:</b> " + data.reply.replace(/\\n/g, "<br>") + "</div>";

            if ("speechSynthesis" in window) {
              const utterance = new SpeechSynthesisUtterance(data.reply);
              window.speechSynthesis.speak(utterance);
            }

          } catch (err) {
            chatBox.innerHTML += "<div class='message bot'><b>Bot:</b> ⚠️ Error connecting to server.</div>";
          }
          chatBox.scrollTop = chatBox.scrollHeight;
        }

        function startSpeechRecognition() {
          if (!('webkitSpeechRecognition' in window)) {
            alert("⚠️ Your browser does not support speech recognition.");
            return;
          }
          const recognition = new webkitSpeechRecognition();
          recognition.lang = "en-IN";
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;

          recognition.start();
          recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById("query").value = transcript;
            sendMessage();
          };
          recognition.onerror = function(event) {
            console.error(event.error);
            alert("⚠️ Speech recognition error: " + event.error);
          };
        }
      </script>
    </body>
    </html>
    """
    return render_template_string(html)

# --------------------------
# Chat API
# --------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        query = data.get("query", "")
        reply = restaurant_bot(query)
        return jsonify({"reply": reply})
    except Exception as e:
        print("Error in /chat:", e)
        return jsonify({"reply": "⚠️ Server error. Please try again."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

