import threading
import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
import requests
from datetime import datetime

# --- CONFIGURATION ---
API_KEY = "47ea018b0543eb33d9e0a58208560fcf"
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "Default"

# Global unit state: "metric" for Celsius, "imperial" for Fahrenheit
current_units = "metric"
last_fetched_data = None

# Popular city suggestions for inline auto-completion (ghost text)
POPULAR_CITIES = [
    "London", "New York", "Tokyo", "Paris", "Dallas", "Houston", "Austin", 
    "Chicago", "Los Angeles", "San Francisco", "Toronto", "Vancouver", 
    "Sydney", "Melbourne", "Dubai", "Manama", "Singapore", "Berlin", 
    "Madrid", "Rome", "Beijing", "Shanghai", "Hong Kong", "Seoul", 
    "Mumbai", "Delhi", "Cairo", "Buenos Aires", "São Paulo", "Mexico City"
]


def init_database():
    """Automatically creates the database and table on startup if they don't exist."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        cursor.execute(f"USE `{DB_NAME}`")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_logs (
                city VARCHAR(100),
                temperature VARCHAR(50),
                condition_text VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database Initialization Error: {e}")


def format_ordinal_day(dt):
    """Formats a datetime object into a clean string like '26th July 2026, 17:14:33'."""
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    return dt.strftime(f"{{day}}{suffix} %B %Y, %H:%M:%S").format(day=day)


def get_weather(event=None):
    """Triggers the weather fetch in a background thread to prevent GUI freezing."""
    city = city_entry.get().strip()
    if not city:
        messagebox.showerror("Error", "Please enter a city name.")
        return

    # Clear ghost text if present
    autocomplete_var.set("")
    fetch_btn.config(state="disabled")
    threading.Thread(target=fetch_weather_thread, args=(city,), daemon=True).start()


def fetch_weather_thread(city):
    """Background worker to fetch weather data, log to MySQL, and reset the search box afterwards."""
    global current_units, last_fetched_data
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units={current_units}"
        response = requests.get(url, timeout=5)
        data = response.json()

        if response.status_code != 200 or data.get("cod") != 200:
            error_msg = data.get("message", "City not found!")
            root.after(0, lambda: messagebox.showerror("Error", f"API Error: {error_msg}"))
            root.after(0, lambda: fetch_btn.config(state="normal"))
            return

        last_fetched_data = data
        city_name = data["name"]
        country = data["sys"].get("country", "")
        temp_val = round(data["main"]["temp"], 1)
        feels_val_num = round(data["main"]["feels_like"], 1)
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        pressure_hpa = data["main"]["pressure"]
        pressure_mmhg = round(pressure_hpa * 0.750062)
        condition = data["weather"][0]["description"].capitalize()
        current_date = datetime.now().strftime("%A, %B %d")

        temp_symbol = "°C" if current_units == "metric" else "°F"
        wind_unit = "m/s" if current_units == "metric" else "mph"
        formatted_temp_str = f"{temp_val} {temp_symbol} (Feels: {feels_val_num}{temp_symbol})"
        full_city_name = f"{city_name}, {country}"

        # Update Card Display UI
        root.after(0, lambda: date_label.config(text=current_date))
        root.after(0, lambda: location_label.config(text=full_city_name))
        root.after(0, lambda: temp_label.config(text=f"{temp_val}°"))
        root.after(0, lambda: condition_label.config(text=condition))
        
        # Update extra metrics
        root.after(0, lambda: wind_val.config(text=f"{wind_speed} {wind_unit}"))
        root.after(0, lambda: hum_val.config(text=f"{humidity}%"))
        root.after(0, lambda: pres_val.config(text=f"{pressure_mmhg} mmHg"))
        root.after(0, lambda: feels_val.config(text=f"{feels_val_num}°"))

        # Connect to Database to check previous logs for this city
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT temperature, timestamp FROM weather_logs WHERE city = %s ORDER BY timestamp DESC LIMIT 2",
            (full_city_name,)
        )
        recent_records = cursor.fetchall()

        is_duplicate = False
        duplicate_info = ""

        for rec in recent_records:
            rec_temp_str = rec[0]
            if rec_temp_str == formatted_temp_str:
                is_duplicate = True
                duplicate_info = rec[0]
                break
            
            try:
                rec_num = float(rec_temp_str.split()[0])
                rec_is_fah = "°F" in rec_temp_str
                
                rec_c = (rec_num - 32) * 5.0 / 9.0 if rec_is_fah else rec_num
                curr_c = (temp_val - 32) * 5.0 / 9.0 if current_units == "imperial" else temp_val
                
                if round(rec_c, 1) == round(curr_c, 1):
                    if rec_is_fah != (current_units == "imperial"):
                        pass
                    else:
                        is_duplicate = True
                        duplicate_info = rec[0]
                        break
            except Exception:
                pass

        if is_duplicate:
            root.after(0, lambda: messagebox.showinfo(
                "Duplicate Skipped", 
                f"The temperature for {full_city_name} in {temp_symbol} has already been recorded ({duplicate_info})."
            ))
        else:
            query = "INSERT INTO weather_logs (city, temperature, condition_text) VALUES (%s, %s, %s)"
            cursor.execute(query, (full_city_name, formatted_temp_str, condition))
            conn.commit()

        cursor.close()
        conn.close()

    except requests.exceptions.Timeout:
        root.after(0, lambda: messagebox.showerror("Error", "Request timed out. Check your connection."))
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("API or Database Error", str(e)))
    finally:
        root.after(0, lambda: fetch_btn.config(state="normal"))
        root.after(0, lambda: city_entry.delete(0, tk.END))
        root.after(0, lambda: autocomplete_var.set(""))


def toggle_units():
    """Toggles between metric (Celsius) and imperial (Fahrenheit) and instantly updates displayed data if available."""
    global current_units, last_fetched_data
    if current_units == "metric":
        current_units = "imperial"
        unit_btn.config(text="Unit: °F", bg="#e67e22", activebackground="#d35400")
    else:
        current_units = "metric"
        unit_btn.config(text="Unit: °C", bg="#2980b9", activebackground="#3498db")
    
    if last_fetched_data:
        city_name = last_fetched_data["name"]
        country = last_fetched_data["sys"].get("country", "")
        
        temp_c = last_fetched_data["main"]["temp"]
        feels_c = last_fetched_data["main"]["feels_like"]
        wind_ms = last_fetched_data["wind"]["speed"]

        if current_units == "imperial":
            temp_val = round((temp_c * 9.0 / 5.0) + 32, 1)
            feels_val_num = round((feels_c * 9.0 / 5.0) + 32, 1)
            wind_speed = round(wind_ms * 2.23694, 1)
            wind_unit = "mph"
        else:
            temp_val = round(temp_c, 1)
            feels_val_num = round(feels_c, 1)
            wind_speed = wind_ms
            wind_unit = "m/s"

        temp_symbol = "°C" if current_units == "metric" else "°F"
        formatted_temp_str = f"{temp_val} {temp_symbol} (Feels: {feels_val_num}{temp_symbol})"
        full_city_name = f"{city_name}, {country}"

        temp_label.config(text=f"{temp_val}°")
        wind_val.config(text=f"{wind_speed} {wind_unit}")
        feels_val.config(text=f"{feels_val_num}°")

        def check_conversion_log():
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
                )
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT temperature FROM weather_logs WHERE city = %s ORDER BY timestamp DESC LIMIT 2",
                    (full_city_name,)
                )
                recent_records = cursor.fetchall()
                cursor.close()
                conn.close()

                exists = any(rec[0] == formatted_temp_str for rec in recent_records)
                if not exists and recent_records:
                    conn = mysql.connector.connect(
                        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
                    )
                    cursor = conn.cursor()
                    query = "INSERT INTO weather_logs (city, temperature, condition_text) VALUES (%s, %s, %s)"
                    cursor.execute(query, (full_city_name, formatted_temp_str, last_fetched_data["weather"][0]["description"].capitalize()))
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception:
                pass

        threading.Thread(target=check_conversion_log, daemon=True).start()


def show_history():
    """Opens a styled dark-teal history window with dropdown sorting options."""
    history_win = tk.Toplevel(root)
    history_win.title("Search History")
    history_win.geometry("740x430")
    history_win.config(bg="#0c2d30")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background="#113a3d",
        foreground="#ffffff",
        fieldbackground="#113a3d",
        rowheight=25,
        font=("Arial", 10)
    )
    style.configure(
        "Dark.Treeview.Heading",
        background="#134e5e",
        foreground="#ffffff",
        font=("Arial", 10, "bold")
    )
    style.map("Dark.Treeview", background=[('selected', '#11998e')])

    control_frame = tk.Frame(history_win, bg="#0c2d30")
    control_frame.pack(fill="x", padx=15, pady=(15, 5))

    sort_lbl = tk.Label(control_frame, text="Sort Options:", font=("Arial", 10, "bold"), bg="#0c2d30", fg="#a2b9bc")
    sort_lbl.pack(side="left", padx=(0, 8))

    sort_options = [
        "Default (Newest to Oldest)",
        "City: Alphabetical (A-Z)",
        "City: Reverse Alphabetical (Z-A)",
        "Temperature: Increasing (Lowest to Highest)",
        "Temperature: Decreasing (Highest to Lowest)",
        "Timestamp: Closer Date to Further Away",
        "Timestamp: Further Away to Closer Date"
    ]
    
    sort_var = tk.StringVar(value=sort_options[0])

    table_frame = tk.Frame(history_win, bg="#0c2d30")
    table_frame.pack(fill="both", expand=True, padx=15, pady=10)

    columns = ("City", "Temperature", "Condition", "Timestamp")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Dark.Treeview")

    tree.column("City", width=170, anchor="center", stretch=False)
    tree.column("Temperature", width=200, anchor="center", stretch=False)
    tree.column("Condition", width=150, anchor="center", stretch=False)
    tree.column("Timestamp", width=180, anchor="center", stretch=False)

    for col in columns:
        tree.heading(col, text=col)

    vsbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsbar = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsbar.set, xscrollcommand=hsbar.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsbar.grid(row=0, column=1, sticky="ns")
    hsbar.grid(row=1, column=0, sticky="ew")

    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    def load_and_sort_data(selection):
        for item in tree.get_children():
            tree.delete(item)
        try:
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
            cursor = conn.cursor()

            if selection == "City: Alphabetical (A-Z)":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY city ASC"
            elif selection == "City: Reverse Alphabetical (Z-A)":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY city DESC"
            elif selection == "Temperature: Increasing (Lowest to Highest)":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY CAST(temperature AS DECIMAL(5,2)) ASC"
            elif selection == "Temperature: Decreasing (Highest to Lowest)":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY CAST(temperature AS DECIMAL(5,2)) DESC"
            elif selection == "Timestamp: Closer Date to Further Away":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY timestamp DESC"
            elif selection == "Timestamp: Further Away to Closer Date":
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY timestamp ASC"
            else:
                query = "SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY timestamp DESC"

            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                row_list = list(row)
                if isinstance(row_list[3], datetime):
                    row_list[3] = format_ordinal_day(row_list[3])
                tree.insert("", "end", values=row_list)
            cursor.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not load history: {e}", parent=history_win)

    sort_dropdown = ttk.Combobox(
        control_frame, textvariable=sort_var, values=sort_options,
        state="readonly", width=35, font=("Arial", 10)
    )
    sort_dropdown.pack(side="left")
    sort_dropdown.bind("<<ComboboxSelected>>", lambda event: load_and_sort_data(sort_var.get()))

    load_and_sort_data(sort_options[0])


def delete_history_item():
    """Opens a window listing all recorded history with city, temperature, and timestamp details for precise single deletion or full history wipe, supporting the Enter key."""
    del_win = tk.Toplevel(root)
    del_win.title("Delete History Records")
    del_win.geometry("560x420")
    del_win.config(bg="#0c2d30")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background="#113a3d",
        foreground="#ffffff",
        fieldbackground="#113a3d",
        rowheight=25,
        font=("Arial", 9)
    )
    style.configure(
        "Dark.Treeview.Heading",
        background="#134e5e",
        foreground="#ffffff",
        font=("Arial", 9, "bold")
    )
    style.map("Dark.Treeview", background=[('selected', '#11998e')])

    lbl = tk.Label(del_win, text="Click a record below and press Enter (or click button) to delete:", font=("Arial", 10, "bold"), bg="#0c2d30", fg="#ffffff")
    lbl.pack(pady=10)

    table_frame = tk.Frame(del_win, bg="#0c2d30")
    table_frame.pack(fill="both", expand=True, padx=15, pady=5)

    columns = ("City", "Temperature", "Condition", "Timestamp")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Dark.Treeview")

    tree.column("City", width=140, anchor="center", stretch=False)
    tree.column("Temperature", width=170, anchor="center", stretch=False)
    tree.column("Condition", width=100, anchor="center", stretch=False)
    tree.column("Timestamp", width=150, anchor="center", stretch=False)

    for col in columns:
        tree.heading(col, text=col)

    vsbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsbar.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsbar.grid(row=0, column=1, sticky="ns")

    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    def load_records():
        for item in tree.get_children():
            tree.delete(item)
        try:
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("SELECT city, temperature, condition_text, timestamp FROM weather_logs ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            for row in rows:
                row_list = list(row)
                if isinstance(row_list[3], datetime):
                    row_list[3] = format_ordinal_day(row_list[3])
                tree.insert("", "end", values=row_list)
            cursor.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not load records: {e}", parent=del_win)

    load_records()

    def delete_selected(event=None):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please click on a record in the list to select it for deletion.", parent=del_win)
            return

        item_values = tree.item(selected_item, "values")
        city_name = item_values[0]
        temp_val = item_values[1]

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this record?\n\nCity: {city_name}\nTemperature: {temp_val}", parent=del_win)
        if confirm:
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
                )
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM weather_logs WHERE city = %s AND temperature = %s LIMIT 1",
                    (city_name, temp_val)
                )
                conn.commit()
                cursor.close()
                conn.close()

                load_records()
                messagebox.showinfo("Success", "Successfully deleted the selected record.", parent=del_win)
            except Exception as e:
                messagebox.showerror("Database Error", str(e), parent=del_win)

    tree.bind("<Return>", delete_selected)

    btn_frame = tk.Frame(del_win, bg="#0c2d30")
    btn_frame.pack(pady=10)

    del_selected_btn = tk.Button(
        btn_frame, text="Delete Selected Record", font=("Arial", 10, "bold"),
        bg="#c0392b", fg="white", activebackground="#e74c3c", relief="flat", command=delete_selected, cursor="hand2"
    )
    del_selected_btn.pack(side="left", padx=5, ipadx=5, ipady=2)

    def clear_all_history():
        confirm = messagebox.askyesno("Clear All", "Are you sure you want to delete ALL search history records?", parent=del_win)
        if confirm:
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
                )
                cursor = conn.cursor()
                cursor.execute("DELETE FROM weather_logs")
                conn.commit()
                cursor.close()
                conn.close()
                load_records()
                messagebox.showinfo("Success", "All history logs have been cleared.", parent=del_win)
            except Exception as e:
                messagebox.showerror("Database Error", str(e), parent=del_win)

    clear_all_btn = tk.Button(
        btn_frame, text="Clear All History", font=("Arial", 10, "bold"),
        bg="#7f8c8d", fg="white", activebackground="#95a5a6", relief="flat", command=clear_all_history, cursor="hand2"
    )
    clear_all_btn.pack(side="left", padx=5, ipadx=5, ipady=2)


# --- INITIALIZATION & GUI SETUP ---
init_database()

root = tk.Tk()
root.title("Weather Card Dashboard")
root.geometry("420x580")
root.config(bg="#0c2d30")

search_frame = tk.Frame(root, bg="#0c2d30")
search_frame.pack(pady=15)

# Frame to hold the ghost text entry overlay
entry_container = tk.Frame(search_frame, bg="white")
entry_container.pack(side="left", padx=5)

autocomplete_var = tk.StringVar(value="")
ghost_label = tk.Label(entry_container, textvariable=autocomplete_var, font=("Arial", 12), bg="white", fg="#b0b0b0", anchor="w")
ghost_label.place(x=2, y=3, relheight=1.0)

city_entry = tk.Entry(entry_container, font=("Arial", 12), width=16, relief="flat", bg="white", highlightthickness=0)
city_entry.pack(side="left", ipady=3)
city_entry.insert(0, "")

# Inline auto-completion logic with ghost text preview as you type
def update_ghost_text(event=None):
    current_text = city_entry.get()
    if not current_text:
        autocomplete_var.set("")
        return
    
    match = ""
    for city in POPULAR_CITIES:
        if city.lower().startswith(current_text.lower()):
            match = city
            break
            
    if match and len(match) > len(current_text):
        # Display the remaining part in grey ghost text behind/beside
        ghost_suggestion = current_text + match[len(current_text):]
        autocomplete_var.set(ghost_suggestion)
    else:
        autocomplete_var.set("")

def handle_key_press(event):
    if event.keysym in ("Tab", "Return"):
        ghost_text = autocomplete_var.get()
        if ghost_text:
            city_entry.delete(0, tk.END)
            city_entry.insert(0, ghost_text)
            autocomplete_var.set("")
            if event.keysym == "Return":
                get_weather()
            return "break"
    elif event.keysym == "BackSpace":
        root.after(1, update_ghost_text)

city_entry.bind("<KeyRelease>", update_ghost_text)
city_entry.bind("<KeyPress>", handle_key_press)
city_entry.bind("<Return>", get_weather)

fetch_btn = tk.Button(
    search_frame, text="Search", font=("Arial", 10, "bold"),
    bg="#11998e", fg="white", activebackground="#38ef7d", relief="flat", command=get_weather, cursor="hand2"
)
fetch_btn.pack(side="left", padx=5, ipady=2)

unit_btn = tk.Button(
    search_frame, text="Unit: °C", font=("Arial", 10, "bold"),
    bg="#2980b9", fg="white", activebackground="#3498db", relief="flat", command=toggle_units, cursor="hand2"
)
unit_btn.pack(side="left", padx=5, ipady=2)

action_frame = tk.Frame(root, bg="#0c2d30")
action_frame.pack(pady=2)

history_btn = tk.Button(
    action_frame, text="View History", font=("Arial", 10, "bold"),
    bg="#134e5e", fg="white", activebackground="#11998e", relief="flat", command=show_history, cursor="hand2"
)
history_btn.pack(side="left", padx=5, ipady=2)

delete_btn = tk.Button(
    action_frame, text="Delete History", font=("Arial", 10, "bold"),
    bg="#c0392b", fg="white", activebackground="#e74c3c", relief="flat", command=delete_history_item, cursor="hand2"
)
delete_btn.pack(side="left", padx=5, ipady=2)

card_frame = tk.Frame(root, bg="#0c2d30")
card_frame.pack(fill="both", expand=True, padx=20, pady=5)

date_label = tk.Label(card_frame, text="", font=("Arial", 11), bg="#0c2d30", fg="#a2b9bc")
date_label.pack()

location_label = tk.Label(card_frame, text="Enter a City", font=("Arial", 18, "bold"), bg="#0c2d30", fg="#ffffff")
location_label.pack(pady=5)

temp_label = tk.Label(card_frame, text="--°", font=("Arial", 60), bg="#0c2d30", fg="#ffffff")
temp_label.pack(pady=5)

condition_label = tk.Label(card_frame, text="Waiting for search...", font=("Arial", 14), bg="#0c2d30", fg="#a2b9bc")
condition_label.pack(pady=2)

sep = ttk.Separator(card_frame, orient="horizontal")
sep.pack(fill="x", pady=15)

details_frame = tk.Frame(card_frame, bg="#0c2d30")
details_frame.pack(fill="x", padx=10)

def add_detail_row(parent, label_text):
    row_frame = tk.Frame(parent, bg="#0c2d30")
    row_frame.pack(fill="x", pady=6)
    
    lbl = tk.Label(row_frame, text=label_text, font=("Arial", 11), bg="#0c2d30", fg="#a2b9bc")
    lbl.pack(side="left")
    
    val = tk.Label(row_frame, text="--", font=("Arial", 11, "bold"), bg="#0c2d30", fg="#ffffff")
    val.pack(side="right")
    return val

wind_val = add_detail_row(details_frame, "Wind")
hum_val = add_detail_row(details_frame, "Humidity")
pres_val = add_detail_row(details_frame, "Atm pressure")
feels_val = add_detail_row(details_frame, "Feels Like")

root.mainloop()
