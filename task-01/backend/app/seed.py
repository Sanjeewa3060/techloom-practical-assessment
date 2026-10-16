"""StudyHub sample catalogue (school accessories) with product images.

Images live in the frontend's public/images/ folder and are referenced by path
(e.g. /images/backpack.svg). To use your own photos, drop e.g. backpack.jpg into that folder
and change the file name here. Run `python -m app.seed --reset` to wipe products,
carts and orders and reload this catalogue.
"""
import sys

from sqlalchemy import delete, func, select

from .database import SessionLocal
from .models import CartItem, Order, OrderItem, Payment, Product

# (name, price, stock, category, description, image file)
SAMPLE = [
    ('Backpack (Student)', 24.99, 18, 'Bags', 'Roomy 25L backpack with padded straps, a laptop sleeve and a front zip pocket.', 'backpack.svg'),
    ('Spiral Notebook (5 Pack)', 7.5, 40, 'Notebooks & Paper', 'Five A4 wire-bound notebooks, 80 ruled pages each, in assorted colours.', 'notebooks.svg'),
    ('Ballpoint Pens (Pack of 10)', 3.99, 120, 'Writing', 'Smooth-writing blue ballpoint pens with a medium 1.0 mm tip.', 'ballpoint-pens.svg'),
    ('Pencil Case', 5.99, 35, 'Bags', 'Soft zip pencil case with room for pens, pencils and an eraser.', 'pencil-case.svg'),
    ('Colour Pencils (12 Pack)', 4.5, 60, 'Art Supplies', 'Twelve bright, break-resistant colour pencils in a sturdy box.', 'colour-pencils.svg'),
    ('Mechanical Pencil', 1.99, 90, 'Writing', '0.7 mm mechanical pencil with a comfortable grip and a built-in eraser.', 'mechanical-pencil.svg'),
    ('Eraser', 0.99, 150, 'Tools & Math', 'Soft, dust-free eraser that lifts pencil marks cleanly.', 'eraser.svg'),
    ('Ruler (30 cm)', 1.5, 70, 'Tools & Math', 'Clear 30 cm ruler with centimetre and inch markings.', 'ruler.svg'),
    ('Glue Stick', 2.5, 55, 'Tools & Math', 'Non-toxic, washable glue stick for paper and card.', 'glue-stick.svg'),
    ('Scientific Calculator', 12.99, 14, 'Tools & Math', '240-function scientific calculator, approved for most school exams.', 'calculator.svg'),
    ('Highlighters (Pack of 4)', 4.25, 45, 'Writing', 'Chisel-tip highlighters in yellow, pink, green and blue.', 'highlighters.svg'),
    ('Marker Set (5 Colours)', 6.75, 25, 'Art Supplies', 'Bold, quick-drying markers for posters and presentations.', 'marker-set.svg'),
    ('Watercolour Paint Set', 8.9, 16, 'Art Supplies', 'Eight vibrant watercolours with a brush and mixing tray.', 'watercolour-set.svg'),
    ('Sticky Notes (6 Pads)', 3.8, 80, 'Notebooks & Paper', 'Six pads of repositionable notes in bright colours.', 'sticky-notes.svg'),
    ('Lunch Box', 11.5, 12, 'Bags', 'Leak-resistant lunch box with a secure snap lid and two compartments.', 'lunch-box.svg'),
    ('Safety Scissors', 3.4, 30, 'Tools & Math', 'Rounded-tip scissors with soft-grip handles, sized for students.', 'scissors.svg'),
    ('Desk Stapler', 5.2, 22, 'Tools & Math', 'Full-strip stapler that holds up to 25 sheets. Staples included.', 'stapler.svg'),
    ('Pencil Sharpener', 1.2, 100, 'Tools & Math', 'Metal-blade sharpener with a lidded shavings container.', 'sharpener.svg'),
    ('Geometry Set', 6.3, 0, 'Tools & Math', 'Ruler, set squares, protractor and compass in a hard case. Sold out for now.', 'geometry-set.svg'),
    ('Correction Tape', 1.8, 2, 'Writing', 'Clean, instant correction tape. Only two left.', 'correction-tape.svg'),
    ('Water Bottle 600ml', 9.5, 28, 'Bags', 'BPA-free bottle with a flip-top lid, easy to carry in a bag.', 'water-bottle.svg'),
    ('A4 Document Folder', 2.2, 65, 'Notebooks & Paper', 'Plastic A4 folder with a press-stud closure for worksheets.', 'folder.svg'),
]


def seed_if_empty() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(Product.id))) == 0:
            # insert in reverse so the first item listed gets the highest id ("Newest" shows it first)
            for name, price, stock, cat, desc, img in reversed(SAMPLE):
                db.add(Product(name=name, price=price, stock_total=stock, category=cat,
                               description=desc, image_url=f"/images/{img}"))
            db.commit()


def reset_and_seed() -> None:
    """Delete ALL carts, orders, payments and products, then insert the sample catalogue."""
    with SessionLocal() as db:
        for model in (Payment, OrderItem, CartItem, Order, Product):
            db.execute(delete(model))
        db.commit()
    seed_if_empty()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_and_seed()
        print("Reset and seeded.")
    else:
        seed_if_empty()
        print("Seeded (only if the products table was empty).")
