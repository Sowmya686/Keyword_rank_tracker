from fastapi import FastAPI, Depends, HTTPException,Request,Form
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey, DateTime,Index
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import bcrypt
import requests
from urllib.parse import quote_plus,urlparse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import xlsxwriter
import os
import time
from openpyxl import Workbook
from openpyxl.styles import Font
from datetime import datetime
from fastapi import APIRouter
# Database Configuration
DB_USER = "root"
DB_PASSWORD = "Sowmya@21"
DB_HOST = "localhost"
MASTER_DB = "rank_db"

# Encode password to handle special characters
encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{encoded_password}@{DB_HOST}/{MASTER_DB}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ORM Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(BigInteger, unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    login_id = Column(String(255), unique=True, index=True, nullable=False)
    projects = relationship("Project", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), index=True, nullable=False)
    project_description = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"),nullable=False)
    author = Column(String(255), nullable=False)
    user = relationship("User", back_populates="projects")
    url_keywords = relationship("URLKeyword", back_populates="project")


class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    keywords = relationship("Keyword", back_populates="url")
    ranks = relationship("Rank", back_populates="url")

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    url_id = Column(Integer, ForeignKey("urls.id"))
    url = relationship("URL", back_populates="keywords")
    ranks = relationship("Rank", back_populates="keyword")

class Rank(Base):
    __tablename__ = "ranks"
    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id"))
    keyword_id = Column(Integer, ForeignKey("keywords.id"))
    ranks = Column(Integer)  # Fixed: renamed from rank to ranks
    page_number = Column(Integer)
    date= Column(DateTime, default=datetime.utcnow)
    
    url = relationship("URL", back_populates="ranks")
    keyword = relationship("Keyword", back_populates="ranks")

    table_args = (Index('idx_url_keyword_date', 'url_id', 'keyword_id', 'date'),)
# Pydantic Schemas
class UserCreate(BaseModel):
    name: str
    email_id: EmailStr
    phone_number: int
    password: str

class LoginSchema(BaseModel):
    name: str
    password: str

class ProjectCreate(BaseModel):
    project_name: str
    project_description: str
    author:str

class URLKeywordCreate(BaseModel):
    project_id: int
    url: str
    keyword: str

# FastAPI App
app = FastAPI()
bcrypt._about_ = {"_version_": "4.0.1"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Single SERPAPI Key
SERP_API_KEY = "d53f7f80a087a80b1362792798e575d8a36149a0b42cf70d96c05a0c6a36f6af"

# Country Mapping
country_domains = {
    "Afghanistan": "google.com.af",
    "Albania": "google.al",
    "Algeria": "google.dz",
    "Andorra": "google.ad",
    "Angola": "google.co.ao",
    "Argentina": "google.com.ar",
    "Armenia": "google.am",
    "Australia": "google.com.au",
    "Austria": "google.at",
    "Azerbaijan": "google.az",
    "Bahamas": "google.bs",
    "Bahrain": "google.com.bh",
    "Bangladesh": "google.com.bd",
    "Barbados": "google.com.bb",
    "Belarus": "google.by",
    "Belgium": "google.be",
    "Belize": "google.com.bz",
    "Benin": "google.bj",
    "Bhutan": "google.bt",
    "Bolivia": "google.com.bo",
    "Bosnia and Herzegovina": "google.ba",
    "Botswana": "google.co.bw",
    "Brazil": "google.com.br",
    "Brunei": "google.com.bn",
    "Bulgaria": "google.bg",
    "Burkina Faso": "google.bf",
    "Burundi": "google.bi",
    "Cambodia": "google.com.kh",
    "Cameroon": "google.cm",
    "Canada": "google.ca",
    "Cape Verde": "google.cv",
    "Central African Republic": "google.cf",
    "Chad": "google.td",
    "Chile": "google.cl",
    "China": "google.cn",
    "Colombia": "google.com.co",
    "Comoros": "google.km",
    "Congo": "google.cg",
    "Costa Rica": "google.co.cr",
    "Croatia": "google.hr",
    "Cuba": "google.com.cu",
    "Cyprus": "google.com.cy",
    "Czechia": "google.cz",
    "Denmark": "google.dk",
    "Djibouti": "google.dj",
    "Dominica": "google.dm",
    "Dominican Republic": "google.com.do",
    "Ecuador": "google.com.ec",
    "Egypt": "google.com.eg",
    "El Salvador": "google.com.sv",
    "Equatorial Guinea": "google.gq",
    "Eritrea": "google.er",
    "Estonia": "google.ee",
    "Eswatini": "google.co.sz",
    "Ethiopia": "google.com.et",
    "Fiji": "google.com.fj",
    "Finland": "google.fi",
    "France": "google.fr",
    "Gabon": "google.ga",
    "Gambia": "google.gm",
    "Georgia": "google.ge",
    "Germany": "google.de",
    "Ghana": "google.com.gh",
    "Greece": "google.gr",
    "Grenada": "google.gd",
    "Guatemala": "google.com.gt",
    "Guinea": "google.gn",
    "Guinea-Bissau": "google.gw",
    "Guyana": "google.gy",
    "Haiti": "google.ht",
    "Honduras": "google.hn",
    "Hungary": "google.hu",
    "Iceland": "google.is",
    "India": "google.co.in",
    "Indonesia": "google.co.id",
    "Iran": "google.ir",
    "Iraq": "google.iq",
    "Ireland": "google.ie",
    "Israel": "google.co.il",
    "Italy": "google.it",
    "Jamaica": "google.com.jm",
    "Japan": "google.co.jp",
    "Jordan": "google.jo",
    "Kazakhstan": "google.kz",
    "Kenya": "google.co.ke",
    "Kiribati": "google.ki",
    "Kuwait": "google.com.kw",
    "Kyrgyzstan": "google.kg",
    "Laos": "google.la",
    "Latvia": "google.lv",
    "Lebanon": "google.com.lb",
    "Lesotho": "google.co.ls",
    "Liberia": "google.com.lr",
    "Libya": "google.com.ly",
    "Liechtenstein": "google.li",
    "Lithuania": "google.lt",
    "Luxembourg": "google.lu",
    "Madagascar": "google.mg",
    "Malawi": "google.mw",
    "Malaysia": "google.com.my",
    "Maldives": "google.mv",
    "Mali": "google.ml",
    "Malta": "google.com.mt",
    "Marshall Islands": "google.mh",
    "Mauritania": "google.mr",
    "Mauritius": "google.mu",
    "Mexico": "google.com.mx",
    "Micronesia": "google.fm",
    "Moldova": "google.md",
    "Monaco": "google.mc",
    "Mongolia": "google.mn",
    "Montenegro": "google.me",
    "Morocco": "google.co.ma",
    "Mozambique": "google.co.mz",
    "Myanmar": "google.com.mm",
    "Namibia": "google.com.na",
    "Nauru": "google.nr",
    "Nepal": "google.com.np",
    "Netherlands": "google.nl",
    "New Zealand": "google.co.nz",
    "Nicaragua": "google.com.ni",
    "Niger": "google.ne",
    "Nigeria": "google.com.ng",
    "North Korea": "google.kp",
    "North Macedonia": "google.mk",
    "Norway": "google.no",
    "Oman": "google.com.om",
    "Pakistan": "google.com.pk",
    "Palau": "google.pw",
    "Panama": "google.com.pa",
    "Papua New Guinea": "google.com.pg",
    "Paraguay": "google.com.py",
    "Peru": "google.com.pe",
    "Philippines": "google.com.ph",
    "Poland": "google.pl",
    "Portugal": "google.pt",
    "Qatar": "google.com.qa",
    "Romania": "google.ro",
    "Russia": "google.ru",
    "Rwanda": "google.rw",
    "Saint Kitts and Nevis": "google.com.kn",
    "Saint Lucia": "google.com.lc",
    "Saint Vincent and the Grenadines": "google.com.vc",
    "Samoa": "google.ws",
    "San Marino": "google.sm",
    "Sao Tome and Principe": "google.st",
    "Saudi Arabia": "google.com.sa",
    "Senegal": "google.sn",
    "Serbia": "google.rs",
    "Seychelles": "google.sc",
    "Sierra Leone": "google.com.sl",
    "Singapore": "google.com.sg",
    "Slovakia": "google.sk",
    "Slovenia": "google.si",
    "Solomon Islands": "google.com.sb",
    "Somalia": "google.so",
    "South Africa": "google.co.za",
    "South Korea": "google.co.kr",
    "Spain": "google.es",
    "Sri Lanka": "google.lk",
    "Sudan": "google.sd",
    "Suriname": "google.sr",
    "Sweden": "google.se",
    "Switzerland": "google.ch",
    "Syria": "google.sy",
    "Taiwan": "google.com.tw",
    "Tajikistan": "google.tj",
    "Tanzania": "google.co.tz",
    "Thailand": "google.co.th",
    "Togo": "google.tg",
    "Tonga": "google.to",
    "Trinidad and Tobago": "google.tt",
    "Tunisia": "google.tn",
    "Turkey": "google.com.tr",
    "Turkmenistan": "google.tm",
    "Tuvalu": "google.tv",
    "Uganda": "google.co.ug",
    "Ukraine": "google.com.ua",
    "United Arab Emirates": "google.ae",
    "United Kingdom": "google.co.uk",
    "United States": "google.com",
    "Uruguay": "google.com.uy",
    "Uzbekistan": "google.co.uz",
    "Vanuatu": "google.vu",
    "Vatican City": "google.va",
    "Venezuela": "google.co.ve",
    "Vietnam": "google.com.vn",
    "Yemen": "google.com.ye",
    "Zambia": "google.co.zm",
    "Zimbabwe": "google.co.zw" 
}

country_codes = {
    "Afghanistan": "af",
    "Albania": "al",
    "Algeria": "dz",
    "Andorra": "ad",
    "Angola": "ao",
    "Argentina": "ar",
    "Armenia": "am",
    "Australia": "au",
    "Austria": "at",
    "Azerbaijan": "az",
    "Bahamas": "bs",
    "Bahrain": "bh",
    "Bangladesh": "bd",
    "Barbados": "bb",
    "Belarus": "by",
    "Belgium": "be",
    "Belize": "bz",
    "Benin": "bj",
    "Bhutan": "bt",
    "Bolivia": "bo",
    "Bosnia and Herzegovina": "ba",
    "Botswana": "bw",
    "Brazil": "br",
    "Brunei": "bn",
    "Bulgaria": "bg",
    "Burkina Faso": "bf",
    "Burundi": "bi",
    "Cambodia": "kh",
    "Cameroon": "cm",
    "Canada": "ca",
    "Cape Verde": "cv",
    "Central African Republic": "cf",
    "Chad": "td",
    "Chile": "cl",
    "China": "cn",
    "Colombia": "co",
    "Comoros": "km",
    "Congo": "cg",
    "Costa Rica": "cr",
    "Croatia": "hr",
    "Cuba": "cu",
    "Cyprus": "cy",
    "Czechia": "cz",
    "Denmark": "dk",
    "Djibouti": "dj",
    "Dominica": "dm",
    "Dominican Republic": "do",
    "Ecuador": "ec",
    "Egypt": "eg",
    "El Salvador": "sv",
    "Equatorial Guinea": "gq",
    "Eritrea": "er",
    "Estonia": "ee",
    "Eswatini": "sz",
    "Ethiopia": "et",
    "Fiji": "fj",
    "Finland": "fi",
    "France": "fr",
    "Gabon": "ga",
    "Gambia": "gm",
    "Georgia": "ge",
    "Germany": "de",
    "Ghana": "gh",
    "Greece": "gr",
    "Grenada": "gd",
    "Guatemala": "gt",
    "Guinea": "gn",
    "Guinea-Bissau": "gw",
    "Guyana": "gy",
    "Haiti": "ht",
    "Honduras": "hn",
    "Hungary": "hu",
    "Iceland": "is",
    "India": "in",
    "Indonesia": "id",
    "Iran": "ir",
    "Iraq": "iq",
    "Ireland": "ie",
    "Israel": "il",
    "Italy": "it",
    "Jamaica": "jm",
    "Japan": "jp",
    "Jordan": "jo",
    "Kazakhstan": "kz",
    "Kenya": "ke",
    "Kiribati": "ki",
    "Kuwait": "kw",
    "Kyrgyzstan": "kg",
    "Laos": "la",
    "Latvia": "lv",
    "Lebanon": "lb",
    "Lesotho": "ls",
    "Liberia": "lr",
    "Libya": "ly",
    "Liechtenstein": "li",
    "Lithuania": "lt",
    "Luxembourg": "lu",
    "Madagascar": "mg",
    "Malawi": "mw",
    "Malaysia": "my",
    "Maldives": "mv",
    "Mali": "ml",
    "Malta": "mt",
    "Marshall Islands": "mh",
    "Mauritania": "mr",
    "Mauritius": "mu",
    "Mexico": "mx",
    "Micronesia": "fm",
    "Moldova": "md",
    "Monaco": "mc",
    "Mongolia": "mn",
    "Montenegro": "me",
    "Morocco": "ma",
    "Mozambique": "mz",
    "Myanmar": "mm",
    "Namibia": "na",
    "Nauru": "nr",
    "Nepal": "np",
    "Netherlands": "nl",
    "New Zealand": "nz",
    "Nicaragua": "ni",
    "Niger": "ne",
    "Nigeria": "ng",
    "North Korea": "kp",
    "North Macedonia": "mk",
    "Norway": "no",
    "Oman": "om",
    "Pakistan": "pk",
    "Palau": "pw",
    "Panama": "pa",
    "Papua New Guinea": "pg",
    "Paraguay": "py",
    "Peru": "pe",
    "Philippines": "ph",
    "Poland": "pl",
    "Portugal": "pt",
    "Qatar": "qa",
    "Romania": "ro",
    "Russia": "ru",
    "Rwanda": "rw",
    "Saint Kitts and Nevis": "kn",
    "Saint Lucia": "lc",
    "Saint Vincent and the Grenadines": "vc",
    "Samoa": "ws",
    "San Marino": "sm",
    "Sao Tome and Principe": "st",
    "Saudi Arabia": "sa",
    "Senegal": "sn",
    "Serbia": "rs",
    "Seychelles": "sc",
    "Sierra Leone": "sl",
    "Singapore": "sg",
    "Slovakia": "sk",
    "Slovenia": "si",
    "Solomon Islands": "sb",
    "Somalia": "so",
    "South Africa": "za",
    "South Korea": "kr",
    "Spain": "es",
    "Sri Lanka": "lk",
    "Sudan": "sd",
    "Suriname": "sr",
    "Sweden": "se",
    "Switzerland": "ch",
    "Syria": "sy",
    "Taiwan": "tw",
    "Tajikistan": "tj",
    "Tanzania": "tz",
    "Thailand": "th",
    "Togo": "tg",
    "Tonga": "to",
    "Trinidad and Tobago": "tt",
    "Tunisia": "tn",
    "Turkey": "tr",
    "Turkmenistan": "tm",
    "Tuvalu": "tv",
    "Uganda": "ug",
    "Ukraine": "ua",
    "United Arab Emirates": "ae",
    "United Kingdom": "gb",
    "United States": "us",
    "Uruguay": "uy",
    "Uzbekistan": "uz",
    "Vanuatu": "vu",
    "Vatican City": "va",
    "Venezuela": "ve",
    "Vietnam": "vn",
    "Yemen": "ye",
    "Zambia": "zm",
    "Zimbabwe": "zw" 
}
@app.post("/search/")
async def search_urls(keyword: str = Form(...), country_name: str = Form(...), pages: int = Form(...)):
    if country_name not in country_domains or country_name not in country_codes:
        raise HTTPException(status_code=400, detail=f"Country '{country_name}' is not supported.")

    google_domain = country_domains[country_name]
    country_code = country_codes[country_name]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }

    results = []
    for page in range(pages):
        start_index = page * 10
        params = {
            "q": keyword,
            "start": start_index,
            "num": 10,
            "gl": country_code,  # Geolocation country code
            "hl": "en",         # Language
            "google_domain": google_domain,  # Explicit Google domain
            "api_key": SERP_API_KEY
        }

        try:
            response = requests.get("https://serpapi.com/search", params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract URLs from organic results
            for result in data.get("organic_results", []):
                results.append(result.get("link"))

        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error while fetching search results: {e}")

        # Respect API rate limits
        time.sleep(2)

    # Generate Excel
    file_name =  f"search_results_{keyword.replace(' ', '')}{country_name.replace(' ', '_')}.xlsx"
    file_path = os.path.join(OUTPUT_DIR, file_name)

    try:
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()

        # Header formatting
        header_format = workbook.add_format({"bold": True, "bg_color": "#D7E4BC", "align": "center"})
        url_format = workbook.add_format({"text_wrap": True, "font_color": "blue", "underline": 1})
        text_format = workbook.add_format({"align": "center"})

        # Write header
        worksheet.write(0, 0, "Keyword", header_format)
        worksheet.write(0, 1, keyword, text_format)
        worksheet.write(0, 2, "Google Domain", header_format)
        worksheet.write(0, 3, country_domains[country_name], text_format)
        worksheet.write(0, 4, "Pages", header_format)
        worksheet.write(0, 5, pages, text_format)
        worksheet.write(2, 0, "S NO", header_format)
        worksheet.write(2, 1, "Backlinks Link", header_format)

        # Write data
        for i, url in enumerate(results, start=1):
            worksheet.write(i + 2, 0, i, text_format)  # Serial Number
            worksheet.write_url(i + 2, 1, url, url_format, string=url)  # Backlinks Link

        # Adjust column widths
        worksheet.set_column(0, 0, 10)  # S NO
        worksheet.set_column(1, 1, 100)  # Backlinks Link
        worksheet.set_column(2, 2, 18)
        worksheet.set_column(3, 3, 18)
        workbook.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel file: {e}")

    return {"file_url": f"/files/{file_name}"}
# Route to serve the generated Excel file
@app.get("/files/{file_name}")
async def download_search_file(file_name: str):
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Search file not found.")
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=file_name)
@app.post("/check-rank")
async def check_rank(domain: str = Form(...), keywords: str = Form(...), country: str = Form(...)):
    # Limit the number of keywords to 500
    keyword_list = keywords.split(",")[:500]
    country_code = country_codes.get(country, "us")  # Default to US if country is not found
    result_data = []

    # Extract domain name from the given URL
    parsed_url = urlparse(domain)
    domain_name = parsed_url.netloc if parsed_url.netloc else domain

    # Create a new workbook for Excel
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = domain_name  # Set sheet title as domain name

    # Add domain and country name to the first two rows
    current_date = datetime.now().strftime("%Y-%m-%d")
    sheet.cell(row=1, column=1, value="Domain").font = Font(bold=True)
    sheet.cell(row=1, column=2, value=domain_name)
    sheet.cell(row=2, column=1, value="Country Code").font = Font(bold=True)
    sheet.cell(row=2, column=2, value=country)
    sheet.cell(row=3, column=1, value="Date").font = Font(bold=True)
    sheet.cell(row=3, column=2, value=current_date)

    # Set up headers for the Excel sheet
    headers = ["Keyword", "Rank", "Page Number"]
    for col_num, header in enumerate(headers, start=1):
        cell = sheet.cell(row=4, column=col_num, value=header)
        cell.font = Font(bold=True)

    # Fetch rankings for each keyword (up to 500 keywords)
    for row_num, keyword in enumerate(keyword_list, start=5):
        keyword = keyword.strip()
        search_url = f"https://serpapi.com/search?api_key={SERP_API_KEY}&q={keyword}&hl=en&gl={country_code}&num=100"
        try:
            response = requests.get(search_url)
            response.raise_for_status()
            data = response.json()

            # Extract ranking and page number information
            rank = None
            page_number = None
            for i, result in enumerate(data.get("organic_results", []), start=1):
                if domain in result.get("link", ""):
                    rank = i
                    page_number = (i - 1) // 10 + 1  # Page number calculation (10 results per page)
                    break

            # Write data to the Excel sheet
            sheet.cell(row=row_num, column=1, value=keyword)
            sheet.cell(row=row_num, column=2, value=rank or "Not Found")
            sheet.cell(row=row_num, column=3, value=page_number or "Not Found")

            result_data.append({
                "keyword": keyword,
                "rank": rank or "Not Found",
                "page_number": page_number or "Not Found"
            })
        except Exception as e:
            sheet.cell(row=row_num, column=1, value=keyword)
            sheet.cell(row=row_num, column=2, value=f"Error: {str(e)}")
            sheet.cell(row=row_num, column=3, value="Error")
            result_data.append({
                "keyword": keyword,
                "rank": f"Error: {str(e)}",
                "page_number": "Error"
            })

    # Save the Excel file with the domain name as its filename
    file_name = f"{domain_name.replace('.', '_')}_rankings.xlsx"
    file_path = os.path.join(OUTPUT_DIR, file_name)
    workbook.save(file_path)

    return {"results": result_data, "file_url": f"/files/{file_name}"}

@app.get("/download-ranking/{file_name}")
async def download_ranking_file(file_name: str):
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Ranking file not found.")
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=file_name)
# Signup Endpoint
@app.post("/signup/")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.email_id == user.email_id) |
        (User.phone_number == user.phone_number) |
        (User.login_id == user.email_id.split('@')[0])
    ).first()

    if existing_user:
        if existing_user.email_id == user.email_id:
            raise HTTPException(status_code=400, detail="Email ID already registered")
        if existing_user.phone_number == user.phone_number:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        if existing_user.login_id == user.email_id.split('@')[0]:
            raise HTTPException(status_code=400, detail="Login ID already taken")
    hashed_password = pwd_context.hash(user.password)
    login_id = user.email_id.split('@')[0]
    db_user = User(
        name=user.name,
        email_id=user.email_id,
        phone_number=user.phone_number,
        password_hash=hashed_password,
        login_id=login_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully", "login_id": login_id}

# Login Endpoint
@app.post("/login/")
def login(user: LoginSchema, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.name == user.name).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"message": "Login successful", "name": db_user.name}

# Project Management
@app.post("/projects/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    print("Received data:", project.dict()) 
    user = db.query(User).filter(User.name == project.author).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_project = Project(
        project_name=project.project_name,
        project_description=project.project_description,
        author=project.author,
        user_id=user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return {"message": "Project created successfully", "project_id": db_project.id}

@app.get("/projects/")
def get_projects(username: str,db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    projects = db.query(Project).filter(Project.user_id == user.id).all()
    return projects
@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

# URL & Keyword Management


@app.post("/track-rank")
async def track_rank(domain: str = Form(...), keywords: str = Form(...), country: str = Form(...), db: Session = Depends(get_db)):
    try:
        keyword_list = {k.strip() for k in keywords.split(",")[:500]}  # Remove duplicates
        existing_url = db.query(URL).filter(URL.url == domain).first()
        if not existing_url:
            existing_url = URL(url=domain)
            db.add(existing_url)
            db.commit()
            db.refresh(existing_url)

        for keyword in keyword_list:
            existing_keyword = db.query(Keyword).filter(Keyword.keyword == keyword, Keyword.url_id == existing_url.id).first()
            if not existing_keyword:
                existing_keyword = Keyword(keyword=keyword, url_id=existing_url.id)
                db.add(existing_keyword)
                db.commit()
                db.refresh(existing_keyword)

        return {"message": "Tracking initialized"}
    except Exception as e:
        return {"error": str(e)}

# Scheduler
scheduler = BackgroundScheduler()

def is_matching_url(target_url, search_result_url):
    target_domain = urlparse(target_url).netloc.replace("www.", "")
    result_domain = urlparse(search_result_url).netloc.replace("www.", "")
    return target_domain == result_domain

def update_ranks():
    db = SessionLocal()
    urls = db.query(URL).all()
    serp_api_key = "d53f7f80a087a80b1362792798e575d8a36149a0b42cf70d96c05a0c6a36f6af"

    for url in urls:
        for keyword in url.keywords:
            print(f"🔍 Checking Rank for: {url.url} - {keyword.keyword}")

            search_url = f"https://serpapi.com/search?api_key={serp_api_key}&q={keyword.keyword}&hl=en&gl=us&num=100"
            response = requests.get(search_url).json()

            rank = None
            page_number = None
            for i, result in enumerate(response.get("organic_results", []), start=1):
                if is_matching_url(url.url, result.get("link", "")):
                    rank = i
                    page_number = (i - 1) // 10 + 1
                    print(f"✅ Rank Found: {rank} (Page {page_number})")
                    break

            if rank is None:
                print(f"❌ No Rank Found for {keyword.keyword}")

            # Store rank in DB
            existing_keyword = db.query(Keyword).filter(Keyword.id == keyword.id).first()
            if existing_keyword:
                new_rank = Rank(url_id=url.id, keyword_id=existing_keyword.id, ranks=rank or -1, page_number=page_number or -1)
                db.add(new_rank)
                db.commit()
                print(f"📌 Rank inserted: {url.url} - {keyword.keyword} => Rank: {rank} (Page {page_number})")

    db.close()

# Schedule rank updates daily
scheduler.add_job(update_ranks, 'cron', hour=6, minute=0)
scheduler.start()
print("🚀 Scheduler started! Runs daily at 6:00 AM.")

# Manual Rank Update API
@app.post("/manual-update-ranks")
def manual_update_ranks():
    try:
        update_ranks()
        return {"message": "Ranks updated manually"}
    except Exception as e:
        return {"error": str(e)}

# Get stored ranks (Supports multiple keywords correctly)
@app.get("/get-ranks")
async def get_ranks(db: Session = Depends(get_db)):
    try:
        ranks = db.query(Rank).all()

        if not ranks:
            print("🚨 No rank data found in database!")
            return {"message": "No rank data found"}

        result = []
        for rank in ranks:
            url = db.query(URL).filter(URL.id == rank.url_id).first()
            keyword = db.query(Keyword).filter(Keyword.id == rank.keyword_id).first()

            result.append({
                "url": url.url if url else "Deleted URL",
                "keyword": keyword.keyword if keyword else "Deleted Keyword",
                "ranks": rank.ranks,
                "page_number": rank.page_number,
                "date": rank.date.strftime("%Y-%m-%d")
            })

        print("✅ Ranks Fetched Successfully")
        return result
    except Exception as e:
        print(f"❌ ERROR in /get-ranks: {e}")
        return {"error": str(e)}

@app.get("/visualize-ranks")
async def visualize_ranks(db: Session = Depends(get_db)):
    try:
        ranks = db.query(Rank).all()
        if not ranks:
            return {"message": "No rank data available"}

        result = []
        for rank in ranks:
            url = db.query(URL).filter(URL.id == rank.url_id).first()
            keyword = db.query(Keyword).filter(Keyword.id == rank.keyword_id).first()

            result.append({
                "url": url.url if url else "Deleted URL",
                "keyword": keyword.keyword if keyword else "Deleted Keyword",
                "ranks": rank.ranks,
                "page_number": rank.page_number,
                "checked_at": rank.date.strftime("%Y-%m-%d")
            })

        return result  
    except Exception as e:
        return {"error": str(e)}
router = APIRouter()

# Run Migrations
Base.metadata.create_all(bind=engine)
@app.get("/")
def read_root():
    return {"message": "Welcome to the Keyword Rank Tracker API!"}