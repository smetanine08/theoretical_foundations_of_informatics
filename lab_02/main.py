INPUT_FILE = "orders.txt"
REPORT_FILE = "orders_report.txt"


FIELD_NAMES = ("номер заказа", "покупатель", "категория",
               "количество", "цена", "статус")


STATUS_ORDER = ("новый", "в обработке", "выполнен", "отменён")


VALID_STATUSES = set(STATUS_ORDER)

DONE_STATUS = "выполнен"
CANCELLED_STATUS = "отменён"
SMALL_LIMIT = 1000
LARGE_LIMIT = 5000


TABLE_HEADER = (f"{'№':<6} {'Покупатель':<18} {'Категория':<14} {'Кол.':>4} "
                f"{'Цена':>10} {'Стоимость':>11} {'Статус':<12} Категория стоимости")


def calc_order_cost(quantity, price):
    """Вернуть стоимость без преждевременного округления."""
    return quantity * price


def category_by_cost(cost):
    """Категория стоимости: Малый, Средний или Крупный."""
    if cost < SMALL_LIMIT:
        return "Малый"
    if cost < LARGE_LIMIT:
        return "Средний"
    return "Крупный"


def build_order(order_id, customer, category, quantity, price, status):
    """Собрать словарь заказа с вычисленными стоимостью и категорией."""
    cost = calc_order_cost(quantity, price)
    return {
        "id": order_id,
        "customer": customer,
        "category": category,
        "quantity": quantity,
        "price": price,
        "status": status,
        "cost": cost,
        "cost_category": category_by_cost(cost),
    }


def read_lines(filename):
    """Прочитать файл; вернуть (список строк, текст ошибки или None)."""
    try:
        with open(filename, "r", encoding="utf-8-sig") as file:

            return file.read().splitlines(), None
    except FileNotFoundError:

        return [], f"Файл «{filename}» не найден."
    except UnicodeDecodeError:

        return [], f"Файл «{filename}» не удаётся прочитать как UTF-8."
    except OSError as error:
        return [], f"Не удалось открыть файл «{filename}»: {error}"


def split_line(line):
    """Разбить строку по «;» и удалить пробелы вокруг каждого поля."""
    return [part.strip() for part in line.split(";")]


def validate_record(fields, seen_ids):
    """Проверить поля записи; вернуть (заказ, None) или (None, причина)."""
    if len(fields) != len(FIELD_NAMES):
        return None, (f"ожидается полей: {len(FIELD_NAMES)}, "
                      f"найдено: {len(fields)}")


    for name, value in zip(FIELD_NAMES, fields):
        if value == "":
            return None, f"пустое поле «{name}»"


    id_text, customer, category, quantity_text, price_text, status_text = fields


    try:
        order_id = int(id_text)
    except ValueError:
        return None, f"номер заказа «{id_text}» не является целым числом"
    if order_id <= 0:
        return None, "номер заказа должен быть положительным"
    if order_id in seen_ids:
        return None, f"повторяющийся номер заказа {order_id}"


    try:
        quantity = int(quantity_text)
    except ValueError:
        return None, f"количество «{quantity_text}» не является целым числом"
    if quantity <= 0:
        return None, "количество должно быть положительным"


    try:
        price = float(price_text)
    except ValueError:

        return None, f"цена «{price_text}» не является числом"


    if not price > 0 or price == float("inf"):
        return None, "цена должна быть положительным числом"


    status = status_text.casefold()
    if status not in VALID_STATUSES:
        return None, f"неизвестный статус «{status_text}»"


    try:
        cost = calc_order_cost(quantity, price)
    except OverflowError:
        return None, "слишком большое количество для вычисления стоимости"
    if cost == float("inf"):
        return None, "стоимость слишком велика для вычислений"
    return build_order(order_id, customer, category, quantity, price, status), None


def load_orders(lines):
    """Разобрать строки файла; вернуть (корректные заказы, сообщения об ошибках)."""
    orders = []
    errors = []
    seen_ids = set()


    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        order, reason = validate_record(split_line(line), seen_ids)
        if order is None:
            errors.append(f"Строка {number}: {reason}.")
        else:

            seen_ids.add(order["id"])
            orders.append(order)
    return orders, errors


def filter_by_status(orders, status):
    """Заказы с указанным статусом (без учёта регистра и пробелов)."""
    wanted = status.strip().casefold()

    return [order for order in orders if order["status"] == wanted]


def filter_by_category(orders, category):
    """Заказы указанной категории (без учёта регистра)."""
    wanted = category.strip().casefold()
    return [order for order in orders if order["category"].casefold() == wanted]


def search_by_customer(orders, part):
    """Заказы покупателей, в имени которых есть заданная часть."""
    wanted = part.strip().casefold()

    if wanted == "":
        return []
    return [order for order in orders if wanted in order["customer"].casefold()]


def filter_large(orders):
    """Заказы со стоимостью не меньше порога крупного заказа."""

    return [order for order in orders if order["cost"] >= LARGE_LIMIT]


def unique_categories(orders):
    """Отсортированный список уникальных категорий (через множество)."""


    return sorted({order["category"] for order in orders}, key=str.casefold)


def cost_sort_key(order):
    """Ключ: стоимость по убыванию, номер по возрастанию."""


    return -order["cost"], order["id"]


def category_sort_key(order):
    """Ключ: категория, затем имя покупателя без учёта регистра."""
    return order["category"].casefold(), order["customer"].casefold()


def sort_by_cost(orders):
    """Новый список: стоимость по убыванию, при равенстве номер по возрастанию."""


    return sorted(orders, key=cost_sort_key)


def sort_by_category(orders):
    """Новый список: категория по возрастанию, внутри неё имя покупателя."""

    return sorted(orders, key=category_sort_key)


def calc_revenue(orders):
    """Выручка: сумма стоимостей только выполненных заказов."""

    done_costs = [order["cost"] for order in orders if order["status"] == DONE_STATUS]

    return sum(done_costs)


def category_stats(orders):
    """Статистика по каждой категории: словарь словарей."""


    stats = {}
    for order in orders:
        category = order["category"]
        if category not in stats:
            stats[category] = {"count": 0, "units": 0, "total": 0.0, "revenue": 0.0}


        item = stats[category]
        item["count"] += 1
        item["units"] += order["quantity"]
        item["total"] += order["cost"]
        if order["status"] == DONE_STATUS:
            item["revenue"] += order["cost"]


    for item in stats.values():
        item["average"] = item["total"] / item["count"]
    return stats


def status_stats(orders):
    """Количество заказов по каждому допустимому статусу (в том числе нулевое)."""


    counts = {status: 0 for status in STATUS_ORDER}
    for order in orders:
        counts[order["status"]] += 1
    return counts


def best_customers(orders):
    """Покупатели с наибольшей суммой выполненных заказов: (имена, сумма)."""

    sums = {}
    for order in orders:
        if order["status"] == DONE_STATUS:

            sums[order["customer"]] = sums.get(order["customer"], 0) + order["cost"]

    if not sums:
        return [], 0.0

    top = max(sums.values())

    names = []
    for name in sums:


        if abs(sums[name] - top) <= 1e-9 * max(1, abs(top)):
            names.append(name)
    return sorted(names), top


def overall_stats(orders):
    """Общие показатели по всем заказам; для пустого списка без ошибок."""
    total_cost = sum([order["cost"] for order in orders])
    names, top_sum = best_customers(orders)
    average = None
    most_expensive = None
    if orders:
        average = total_cost / len(orders)
        most_expensive = sort_by_cost(orders)[0]
    return {
        "total_count": len(orders),
        "done_count": len([o for o in orders if o["status"] == DONE_STATUS]),
        "cancelled_count": len([o for o in orders if o["status"] == CANCELLED_STATUS]),
        "total_cost": total_cost,
        "revenue": calc_revenue(orders),


        "average_cost": average,

        "most_expensive": most_expensive,
        "best_names": names,
        "best_sum": top_sum,
    }


def format_order(order):
    """Одна строка таблицы для заказа."""


    return (f"{order['id']:<6} {order['customer']:<18} {order['category']:<14} "
            f"{order['quantity']:>4} {order['price']:>10.2f} {order['cost']:>11.2f} "
            f"{order['status']:<12} {order['cost_category']}")


def format_table(orders):
    """Таблица заказов в виде списка строк."""
    if not orders:
        return ["   (нет заказов)"]

    return [TABLE_HEADER, "-" * len(TABLE_HEADER)] + [format_order(o) for o in orders]


def format_overall(stats):
    """Общие показатели в виде списка строк."""
    lines = [
        f"Всего заказов: {stats['total_count']}",
        f"Выполненных заказов: {stats['done_count']}",
        f"Отменённых заказов: {stats['cancelled_count']}",
        f"Общая стоимость всех заказов: {stats['total_cost']:.2f}",
        f"Выручка по выполненным заказам: {stats['revenue']:.2f}",
    ]

    if stats["average_cost"] is None:
        lines.append("Средняя стоимость заказа: невозможно вычислить (нет заказов)")
    else:
        lines.append(f"Средняя стоимость заказа: {stats['average_cost']:.2f}")
    top = stats["most_expensive"]
    if top is None:
        lines.append("Самый дорогой заказ: нет заказов")
    else:
        lines.append(f"Самый дорогой заказ: №{top['id']}, {top['customer']}, "
                     f"{top['cost']:.2f}")
    if stats["best_names"]:

        lines.append(f"Лучший покупатель: {', '.join(stats['best_names'])} "
                     f"(сумма выполненных заказов {stats['best_sum']:.2f})")
    else:
        lines.append("Лучший покупатель: определить невозможно "
                     "(нет выполненных заказов, выручка равна нулю)")
    return lines


def format_category_stats(stats):
    """Статистика по категориям в виде списка строк."""
    if not stats:
        return ["   (нет данных)"]
    lines = []

    for name in sorted(stats, key=str.casefold):
        item = stats[name]
        lines.append(f"{name}: заказов {item['count']}, единиц {item['units']}, "
                     f"общая стоимость {item['total']:.2f}, "
                     f"выполненных на {item['revenue']:.2f}, "
                     f"средняя стоимость {item['average']:.2f}")
    return lines


def format_status_stats(counts):
    """Статистика по статусам в виде списка строк."""

    return [f"{status}: {counts[status]}" for status in STATUS_ORDER]


def format_statistics(orders):
    """Полная статистика (общая, по категориям, по статусам) списком строк."""

    return (["Общие показатели:"] + format_overall(overall_stats(orders))
            + ["", "Статистика по категориям:"] + format_category_stats(category_stats(orders))
            + ["", "Статистика по статусам:"] + format_status_stats(status_stats(orders)))


def build_report(orders, errors):
    """Собрать текст отчёта (список строк) по девяти разделам."""

    categories = unique_categories(orders)
    lines = ["ОТЧЁТ ПО ЗАКАЗАМ МАГАЗИНА", "=" * 60, "",
             f"1. Количество корректных записей: {len(orders)}",
             f"2. Количество некорректных записей: {len(errors)}",
             "3. Уникальные категории: " + (", ".join(categories) if categories else "нет"),
             "", "4. Заказы по убыванию стоимости:"]
    lines += format_table(sort_by_cost(orders))
    lines += ["", "5. Крупные заказы (от 5000):"]
    lines += format_table(sort_by_cost(filter_large(orders)))
    stats = overall_stats(orders)
    lines += ["", "6. Общие показатели:"] + format_overall(stats)
    lines += ["", "7. Статистика по категориям:"] + format_category_stats(category_stats(orders))
    lines += ["", "8. Статистика по статусам:"] + format_status_stats(status_stats(orders))
    lines += ["", "9. Ошибки входных данных:"]
    lines += errors if errors else ["   (ошибок нет)"]
    return lines


def save_report(filename, lines):
    """Записать строки в файл; вернуть текст ошибки или None."""


    try:

        with open(filename, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
    except OSError as error:
        return f"Не удалось сохранить отчёт: {error}"
    return None


MENU_TEXT = """
1. Показать все заказы
2. Показать заказы по убыванию стоимости
3. Показать заказы по категориям
4. Найти заказы по статусу
5. Найти заказы по категории
6. Найти заказы покупателя
7. Показать крупные заказы
8. Показать статистику
9. Сохранить отчёт
0. Завершить программу"""


def ask_text(prompt):
    """Запросить у пользователя строку."""


    return input(prompt)


def show_orders(orders, title):
    """Вывести заголовок и таблицу заказов или сообщение, что их нет."""
    print(f"\n{title}:")
    if orders:
        print("\n".join(format_table(orders)))
    else:

        print("Заказы не найдены.")


def handle_command(choice, orders, errors):
    """Выполнить пункт меню; вернуть False, если программу нужно завершить."""


    if choice == "1":
        show_orders(orders, "Все заказы")
    elif choice == "2":
        show_orders(sort_by_cost(orders), "Заказы по убыванию стоимости")
    elif choice == "3":
        show_orders(sort_by_category(orders), "Заказы по категориям")
    elif choice == "4":
        status = ask_text("Введите статус: ")
        show_orders(filter_by_status(orders, status), f"Заказы со статусом «{status.strip()}»")
    elif choice == "5":
        category = ask_text("Введите категорию: ")
        show_orders(filter_by_category(orders, category), f"Заказы категории «{category.strip()}»")
    elif choice == "6":
        part = ask_text("Введите часть имени покупателя: ")

        if part.strip():
            show_orders(search_by_customer(orders, part), f"Заказы по запросу «{part.strip()}»")
        else:
            print("Пустой запрос. Введите хотя бы один символ.")
    elif choice == "7":
        show_orders(sort_by_cost(filter_large(orders)), "Крупные заказы (от 5000)")
    elif choice == "8":
        print("\n" + "\n".join(format_statistics(orders)))
    elif choice == "9":
        error = save_report(REPORT_FILE, build_report(orders, errors))
        print(error if error else f"Отчёт сохранён в файл «{REPORT_FILE}».")
    elif choice == "0":
        print("Работа завершена.")
        return False
    else:

        print(f"Неизвестный пункт меню «{choice}». Выберите число от 0 до 9.")
    return True


def run_menu(orders, errors):
    """Показывать меню и обрабатывать команды, пока пользователь не выйдет."""

    running = True
    while running:
        print(MENU_TEXT)
        try:
            choice = ask_text("Ваш выбор: ").strip()
        except EOFError:

            print("\nВвод закончен. Работа завершена.")
            break
        try:
            running = handle_command(choice, orders, errors)
        except EOFError:
            print("\nВвод закончен. Работа завершена.")
            break


def ids(items):
    """Вернуть номера заказов: вспомогательная функция для assert."""
    return [item["id"] for item in items]


def run_tests():
    """Автоматические проверки основных функций (обычные и граничные случаи)."""

    a = build_order(1, "Иванов Иван", "Книги", 2, 750.5, "выполнен")
    b = build_order(2, "Петрова Анна", "Электроника", 1, 4500.0, "новый")
    c = build_order(3, "Сидоров Олег", "Канцелярия", 5, 120.0, "выполнен")
    d = build_order(4, "Кузнецова Мария", "Книги", 3, 640.0, "отменён")
    e = build_order(5, "Смирнов Павел", "Электроника", 2, 3200.0, "в обработке")
    f = build_order(6, "Тестов Тест", "Книги", 1, 1501.0, "выполнен")
    data = [a, b, c, d, e, f]


    assert calc_order_cost(2, 750.5) == 1501.0
    assert abs(calc_order_cost(3, 0.1) - 0.3) < 1e-9
    assert category_by_cost(calc_order_cost(1, 999.999)) == "Малый"


    assert category_by_cost(0) == "Малый"
    assert category_by_cost(999.99) == "Малый"
    assert category_by_cost(1000) == "Средний"
    assert category_by_cost(4999.99) == "Средний"
    assert category_by_cost(5000) == "Крупный"


    assert ids(filter_by_status(data, "  ВЫПОЛНЕН ")) == [1, 3, 6]
    assert filter_by_status(data, "доставляется") == []
    assert ids(filter_by_category(data, "кНиГи")) == [1, 4, 6]


    assert ids(search_by_customer(data, "ИВАН")) == [1]
    assert search_by_customer(data, "несуществующий") == []


    assert ids(sort_by_cost(data)) == [5, 2, 4, 1, 6, 3]
    assert ids(sort_by_category(data)) == [3, 1, 4, 6, 2, 5]
    assert ids(data) == [1, 2, 3, 4, 5, 6]


    assert calc_revenue(data) == 3602.0
    assert calc_revenue([b, d]) == 0
    assert calc_revenue([]) == 0


    assert best_customers(data) == (["Иванов Иван", "Тестов Тест"], 1501.0)
    assert best_customers([b, d]) == ([], 0.0)


    assert status_stats([b]) == {"новый": 1, "в обработке": 0, "выполнен": 0, "отменён": 0}
    assert overall_stats([])["average_cost"] is None


    order, reason = validate_record(["7", " Ольга ", "Книги", "2", "10.5", "НОВЫЙ"], set())
    assert reason is None and order["status"] == "новый" and order["cost"] == 21.0
    assert validate_record(["1", "А", "Б", "2", "10"], set())[0] is None
    assert "повторяющийся" in validate_record(["1", "А", "Б", "2", "10", "новый"], {1})[1]
    assert "положительным" in validate_record(["1", "А", "Б", "0", "10", "новый"], set())[1]
    assert "неизвестный статус" in validate_record(["1", "А", "Б", "1", "10", "x"], set())[1]
    assert "пустое поле" in validate_record(["1", "", "Б", "1", "10", "новый"], set())[1]


def main():
    """Точка входа: проверки, загрузка данных, запуск меню."""
    run_tests()
    print("Автоматические проверки пройдены.")
    lines, error = read_lines(INPUT_FILE)
    if error:
        print(error)
        return
    orders, errors = load_orders(lines)
    print(f"Корректных записей: {len(orders)}, некорректных: {len(errors)}.")
    for message in errors:
        print(message)


    if not orders:
        print("Корректных записей нет: поиск и статистика вернут пустые результаты.")
    run_menu(orders, errors)


if __name__ == "__main__":
    main()
