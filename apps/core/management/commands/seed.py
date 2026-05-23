"""
Seed the database with demo cities, admins, buyers, listings & inquiries.

Run:
    python manage.py seed
    python manage.py seed --reset   # wipe seed listings and reseed
"""
from decimal import Decimal
from random import choice, randint

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.adminpanel.models import Admin, AppSettings
from apps.cities.models import City
from apps.inquiries.models import Inquiry
from apps.listings.models import Listing, ListingPhoto

User = get_user_model()


CITIES = [
    ("Ahmedabad", "Gujarat", 1553, True),
    ("Mumbai", "Maharashtra", 2840, True),
    ("Delhi", "Delhi NCR", 3120, True),
    ("Bangalore", "Karnataka", 2210, True),
    ("Hyderabad", "Telangana", 1890, True),
    ("Chennai", "Tamil Nadu", 1650, True),
    ("Pune", "Maharashtra", 1420, True),
    ("Kolkata", "West Bengal", 1340, True),
    ("Surat", "Gujarat", 980, False),
    ("Jaipur", "Rajasthan", 870, False),
    ("Lucknow", "Uttar Pradesh", 760, False),
    ("Chandigarh", "Punjab", 540, False),
    ("Gurugram", "Haryana", 720, False),
    ("Noida", "Uttar Pradesh", 680, False),
    ("Ghaziabad", "Uttar Pradesh", 510, False),
    ("Faridabad", "Haryana", 430, False),
    ("Thane", "Maharashtra", 620, False),
    ("Nashik", "Maharashtra", 390, False),
    ("Nagpur", "Maharashtra", 410, False),
    ("Indore", "Madhya Pradesh", 520, False),
    ("Bhopal", "Madhya Pradesh", 380, False),
    ("Vadodara", "Gujarat", 420, False),
    ("Rajkot", "Gujarat", 350, False),
    ("Coimbatore", "Tamil Nadu", 340, False),
    ("Kochi", "Kerala", 310, False),
    ("Visakhapatnam", "Andhra Pradesh", 320, False),
    ("Patna", "Bihar", 280, False),
    ("Bhubaneswar", "Odisha", 260, False),
    ("Dehradun", "Uttarakhand", 240, False),
    ("Amritsar", "Punjab", 220, False),
    ("Ludhiana", "Punjab", 290, False),
    ("Jodhpur", "Rajasthan", 230, False),
    ("Udaipur", "Rajasthan", 190, False),
    ("Agra", "Uttar Pradesh", 250, False),
    ("Mysore", "Karnataka", 270, False),
    ("Gandhinagar", "Gujarat", 290, False),
]


ADMINS = [
    {
        "email": "admin@oldcarbazar.com", "password": "admin@123",
        "name": "Anurodh Singh", "role": "super-admin",
        "avatar_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200",
    },
    {
        "email": "moderator@oldcarbazar.com", "password": "mod@123",
        "name": "Riya Sharma", "role": "moderator",
        "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200",
    },
    {
        "email": "support@oldcarbazar.com", "password": "support@123",
        "name": "Karan Mehta", "role": "support",
        "avatar_url": "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=200",
    },
]


BUYERS = [
    ("Amit Kumar", "amit.kumar@gmail.com", "9876512345", "Delhi"),
    ("Priya Verma", "priya.v@gmail.com", "9988123456", "Mumbai"),
    ("Rohit Singh", "rohit.singh@gmail.com", "9090909090", "Bangalore"),
    ("Sneha Patel", "sneha.patel@gmail.com", "9123456780", "Ahmedabad"),
    ("Arjun Reddy", "arjun.r@gmail.com", "9012345678", "Hyderabad"),
    ("Neha Joshi", "neha.j@gmail.com", "8765432109", "Pune"),
]


CARS = [
    # title, brand, model, year, price (lakhs), kms, fuel, txn, owners, city, featured, cover
    ("2020 Tata Harrier XZ BSVI", "Tata", "Harrier XZ BSVI", 2020, 11, 80000,
     "Diesel", "Manual", "1st Owner", "Ahmedabad", False,
     "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=800"),
    ("2019 Maruti Swift VDI", "Maruti", "Swift VDI", 2019, 5.5, 45000,
     "Diesel", "Manual", "2nd Owner", "Ahmedabad", True,
     "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800"),
    ("2021 Hyundai Creta SX", "Hyundai", "Creta SX", 2021, 14.2, 32000,
     "Petrol", "Automatic", "1st Owner", "Mumbai", False,
     "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=800"),
    ("2018 Honda City ZX CVT", "Honda", "City ZX CVT", 2018, 8.9, 62000,
     "Petrol", "Automatic", "2nd Owner", "Delhi", False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800"),
    ("2017 Toyota Innova Crysta", "Toyota", "Innova Crysta", 2017, 12.5, 110000,
     "Diesel", "Manual", "2nd Owner", "Bangalore", True,
     "https://images.unsplash.com/photo-1541899481282-d53bffe25c6d?w=800"),
    ("2022 Mahindra Thar LX", "Mahindra", "Thar LX", 2022, 13.8, 18000,
     "Petrol", "Manual", "1st Owner", "Pune", False,
     "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800"),
    ("2019 Kia Seltos HTX", "Kia", "Seltos HTX", 2019, 10.2, 55000,
     "Petrol", "Automatic", "1st Owner", "Hyderabad", True,
     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=800"),
    ("2016 Renault Duster RXZ", "Renault", "Duster RXZ", 2016, 6.8, 95000,
     "Diesel", "Manual", "2nd Owner", "Chennai", False,
     "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=800"),
    ("2020 Maruti Ertiga VDI", "Maruti", "Ertiga VDI", 2020, 9.5, 40000,
     "Diesel", "Manual", "1st Owner", "Surat", False,
     "https://images.unsplash.com/photo-1621007947412-baf6869b7751?w=800"),
    ("2018 Ford EcoSport Titanium", "Ford", "EcoSport Titanium", 2018, 7.2, 70000,
     "Diesel", "Manual", "2nd Owner", "Jaipur", False,
     "https://images.unsplash.com/photo-1550355291-bbee04a92027?w=800"),
    ("2021 Tata Nexon EV", "Tata", "Nexon EV", 2021, 11.5, 22000,
     "Electric", "Automatic", "1st Owner", "Kolkata", True,
     "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800"),
    ("2017 Hyundai i20 Sportz", "Hyundai", "i20 Sportz", 2017, 5.9, 58000,
     "Petrol", "Manual", "2nd Owner", "Lucknow", False,
     "https://images.unsplash.com/photo-1609521263047-f8f205293f24?w=800"),
    ("2019 Volkswagen Polo GT", "Volkswagen", "Polo GT", 2019, 7.8, 48000,
     "Petrol", "Manual", "1st Owner", "Chandigarh", False,
     "https://images.unsplash.com/photo-1542362565-b07e54358753?w=800"),
    ("2020 MG Hector Plus", "MG", "Hector Plus", 2020, 13.1, 35000,
     "Petrol", "Automatic", "1st Owner", "Mumbai", False,
     "https://images.unsplash.com/photo-1619767886555-ef069765baa8?w=800"),
    ("2018 Maruti Baleno Alpha", "Maruti", "Baleno Alpha", 2018, 6.4, 52000,
     "Petrol", "Automatic", "1st Owner", "Delhi", True,
     "https://images.unsplash.com/photo-1493238792000-8113da705763?w=800"),
    ("2022 Skoda Kushaq Style", "Skoda", "Kushaq Style", 2022, 12.9, 15000,
     "Petrol", "Automatic", "1st Owner", "Bangalore", False,
     "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800"),
    ("2019 Honda Amaze VX", "Honda", "Amaze VX", 2019, 6.1, 44000,
     "Petrol", "Manual", "2nd Owner", "Ahmedabad", False,
     "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"),
    ("2020 Toyota Fortuner 4x2", "Toyota", "Fortuner 4x2", 2020, 28.5, 60000,
     "Diesel", "Automatic", "1st Owner", "Hyderabad", True,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=800"),
]


SAMPLE_MESSAGES = [
    "Is the car still available for inspection this weekend?",
    "Can you share the service history and insurance copy?",
    "Final price kya hai? Discount possible?",
    "Test drive kal mere ghar par arrange ho sakta hai?",
    "Mileage and condition real-time kaisi hai?",
    "Loan facility available for this car?",
]
SAMPLE_NAMES = [
    "Ankit Sharma", "Pooja Iyer", "Vikas Yadav", "Meera Pillai",
    "Sandeep Kumar", "Divya Nair", "Rajesh Khanna", "Shruti Banerjee",
]


class Command(BaseCommand):
    help = "Seed demo data (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete seed listings + admins + demo buyers before reseeding.",
        )

    def handle(self, *args, **opts):
        if opts["reset"]:
            self.stdout.write(self.style.WARNING("Resetting seed data…"))
            Listing.objects.filter(is_seed=True).delete()
            Admin.objects.filter(email__endswith="@oldcarbazar.com").delete()
            User.objects.filter(email__in=[b[1] for b in BUYERS]).delete()

        self._seed_cities()
        self._seed_admins()
        self._seed_buyers()
        self._seed_listings()
        self._seed_inquiries()
        self._ensure_settings()

        self.stdout.write(self.style.SUCCESS("\n[OK] Seed complete\n"))
        self.stdout.write("Demo credentials:")
        self.stdout.write("  Super admin -> admin@oldcarbazar.com / admin@123")
        self.stdout.write("  Moderator   -> moderator@oldcarbazar.com / mod@123")
        self.stdout.write("  Buyer       -> amit.kumar@gmail.com / password123")

    # ---------------------- per-table seeders ---------------------- #

    def _seed_cities(self):
        created = 0
        for name, state, count, popular in CITIES:
            _, was_created = City.objects.get_or_create(
                name=name,
                defaults={"state": state, "car_count": count, "popular": popular},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Cities seeded: +{created} (total {City.objects.count()})")

    def _seed_admins(self):
        for a in ADMINS:
            obj, was_created = Admin.objects.get_or_create(
                email=a["email"],
                defaults={"name": a["name"], "role": a["role"], "avatar_url": a["avatar_url"]},
            )
            if was_created or not obj.password_hash:
                obj.set_password(a["password"])
                obj.save()
        self.stdout.write(f"  Admins ready ({Admin.objects.count()})")

    def _seed_buyers(self):
        created = 0
        for name, email, phone, city in BUYERS:
            user, was_created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "name": name, "email": email, "city": city,
                    "role": User.Role.BUYER, "status": User.Status.ACTIVE,
                    "email_verified": True, "phone_verified": True,
                },
            )
            if was_created:
                user.set_password("password123")
                user.save()
                created += 1
        self.stdout.write(f"  Buyers seeded: +{created} (total {User.objects.count()})")

    def _seed_listings(self):
        existing = set(
            Listing.objects.filter(is_seed=True).values_list("title", flat=True)
        )
        created = 0
        for (title, brand, model, year, price, kms, fuel, txn, owners,
             city, featured, cover) in CARS:
            if title in existing:
                continue
            listing = Listing.objects.create(
                seller_name="Verified Dealer",
                seller_phone="9876543210",
                seller_email="dealer@oldcarbazar.com",
                title=title, brand=brand, model=model, year=year,
                price_label=f"₹{price} Lakh",
                price_inr=Decimal(price) * Decimal("100000"),
                kms=kms, fuel=fuel, transmission=txn,
                owners=owners,
                ownership="First owner" if owners == "1st Owner"
                else "Second owner" if owners == "2nd Owner"
                else "Third owner",
                location=city, body_type="Hatchback", seats=5,
                cover_image=cover,
                status=Listing.Status.ACTIVE,
                moderation=Listing.Moderation.APPROVED,
                featured=featured, whatsapp=True, is_seed=True,
                views=randint(80, 300),
                inquiries_count=randint(0, 10),
            )
            ListingPhoto.objects.create(
                listing=listing, url=cover, position=0, is_cover=True
            )
            created += 1
        self.stdout.write(f"  Listings seeded: +{created} (total {Listing.objects.count()})")

    def _seed_inquiries(self):
        if Inquiry.objects.exists():
            self.stdout.write(f"  Inquiries already present ({Inquiry.objects.count()})")
            return
        sample = list(Listing.objects.filter(is_seed=True)[:10])
        channels = list(Inquiry.Channel.values)
        statuses = ["new", "responded", "closed"]
        for i, car in enumerate(sample):
            Inquiry.objects.create(
                listing=car,
                listing_title=car.title,
                listing_price=car.price_label,
                buyer_name=SAMPLE_NAMES[i % len(SAMPLE_NAMES)],
                buyer_phone=f"9{str(100000000 + i * 7345)[:9]}",
                buyer_email=(
                    f"{SAMPLE_NAMES[i % len(SAMPLE_NAMES)].split()[0].lower()}"
                    f"@gmail.com"
                ),
                seller_name=car.seller_name,
                message=choice(SAMPLE_MESSAGES),
                channel=channels[i % len(channels)],
                status=statuses[i % len(statuses)],
                city=car.location,
            )
        self.stdout.write(f"  Inquiries seeded: {Inquiry.objects.count()}")

    def _ensure_settings(self):
        AppSettings.singleton()
        self.stdout.write("  App settings ready")
