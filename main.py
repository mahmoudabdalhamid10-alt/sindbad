from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
import sqlite3, os, hashlib, hmac, secrets, json
from datetime import datetime, timedelta

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,'sindbad.db')
SECRET=os.environ.get('SINDBAD_SECRET','local-dev-change-before-deployment').encode()
app=FastAPI(title='Sindbad | AI-powered Global B2B Marketplace',version='2.0.0')
app.mount('/static',StaticFiles(directory=os.path.join(BASE,'static')),name='static')

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def pw_hash(password,salt): return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),180000).hex()
def token_for(uid):
    payload=f'{uid}:{int((datetime.utcnow()+timedelta(days=7)).timestamp())}'
    return payload+'.'+hmac.new(SECRET,payload.encode(),'sha256').hexdigest()
def user_by_id(uid):
    c=db(); r=c.execute('SELECT id,name,email,role,company,country,created_at FROM users WHERE id=?',(uid,)).fetchone(); c.close(); return dict(r) if r else None
def current_user(request:Request):
    tok=request.cookies.get('sindbad_session')
    if not tok:return None
    try:
        payload,sig=tok.rsplit('.',1); exp_sig=hmac.new(SECRET,payload.encode(),'sha256').hexdigest()
        if not hmac.compare_digest(sig,exp_sig):return None
        uid,exp=payload.split(':')
        if int(exp)<int(datetime.utcnow().timestamp()):return None
        return user_by_id(int(uid))
    except Exception:return None
def require_user(request:Request):
    u=current_user(request)
    if not u:raise HTTPException(401,'Please sign in first')
    return u

class Register(BaseModel):
    name:str=Field(min_length=2,max_length=100); email:EmailStr; password:str=Field(min_length=8,max_length=128); role:str; company:str=Field(min_length=2,max_length=120); country:str=''
class Login(BaseModel): email:EmailStr; password:str
class ProductIn(BaseModel): title:str=Field(min_length=3,max_length=160); category:str; description:str=''; price:float=Field(gt=0); currency:str='USD'; moq:int=Field(default=1,ge=1); stock:int=Field(default=0,ge=0); image:str=''; origin:str=''; lead_time:str='7-15 days'; tags:str=''
class OrderItem(BaseModel): product_id:int; quantity:int=Field(ge=1)
class OrderIn(BaseModel): items:list[OrderItem]
class RFQIn(BaseModel): title:str; details:str=''; quantity:int=Field(default=1,ge=1); target_price:float|None=None; destination:str=''
class EventIn(BaseModel): product_id:int; event_type:str='view'


def init_db():
 c=db(); q=c.cursor(); q.executescript('''
 CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('buyer','supplier')),company TEXT NOT NULL,country TEXT DEFAULT '',created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,supplier_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,category TEXT NOT NULL,description TEXT DEFAULT '',price REAL NOT NULL,currency TEXT DEFAULT 'USD',moq INTEGER DEFAULT 1,stock INTEGER DEFAULT 0,image TEXT DEFAULT '',origin TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT NOT NULL,lead_time TEXT DEFAULT '7-15 days',tags TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,buyer_id INTEGER NOT NULL REFERENCES users(id),total REAL NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',items_json TEXT NOT NULL,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS rfqs(id INTEGER PRIMARY KEY,buyer_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,details TEXT DEFAULT '',quantity INTEGER DEFAULT 1,target_price REAL,destination TEXT DEFAULT '',status TEXT DEFAULT 'open',created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,sender_id INTEGER NOT NULL REFERENCES users(id),receiver_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER NOT NULL REFERENCES users(id),product_id INTEGER NOT NULL REFERENCES products(id),created_at TEXT NOT NULL,PRIMARY KEY(user_id,product_id));
 CREATE TABLE IF NOT EXISTS interactions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),product_id INTEGER NOT NULL REFERENCES products(id),event_type TEXT NOT NULL,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS quotations(id INTEGER PRIMARY KEY,rfq_id INTEGER NOT NULL REFERENCES rfqs(id),supplier_id INTEGER NOT NULL REFERENCES users(id),price REAL NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',lead_time TEXT DEFAULT '',notes TEXT DEFAULT '',created_at TEXT NOT NULL,UNIQUE(rfq_id,supplier_id));
 CREATE INDEX IF NOT EXISTS idx_products_category ON products(category); CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id,created_at);
 ''')
 # Safe schema upgrades for databases created by earlier builds
 cols={r['name'] for r in q.execute('PRAGMA table_info(products)').fetchall()}
 for name,decl in [('lead_time',"TEXT DEFAULT '7-15 days'"),('tags',"TEXT DEFAULT ''")]:
  if name not in cols:q.execute(f'ALTER TABLE products ADD COLUMN {name} {decl}')
 # demo accounts
 demo=[('Demo Supplier','demo@sindbad.com','supplier','Sindbad Global Trading','Egypt','demo1234'),('Atlas Wholesale','atlas@sindbad.com','supplier','Atlas Wholesale Co.','Turkey','demo1234'),('Nova Industrial','nova@sindbad.com','supplier','Nova Industrial Supply','China','demo1234'),('Demo Buyer','buyer@sindbad.com','buyer','Cairo Retail Group','Egypt','buyer1234')]
 for name,email,role,company,country,pw in demo:
  if not q.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
   salt=secrets.token_hex(16); q.execute('INSERT INTO users(name,email,salt,password_hash,role,company,country,created_at) VALUES(?,?,?,?,?,?,?,?)',(name,email,salt,pw_hash(pw,salt),role,company,country,datetime.utcnow().isoformat()))
 if q.execute('SELECT COUNT(*) n FROM products').fetchone()['n']==0:
  suppliers={r['email']:r['id'] for r in q.execute("SELECT id,email FROM users WHERE role='supplier'").fetchall()}
  # title, category, description, price, MOQ, stock, image, origin, supplier, lead, tags
  items=[
  ('Industrial safety gloves','Safety & PPE','Abrasion-resistant nitrile coated work gloves for industrial and construction use.',1.25,500,12000,'photo-1584634731339-252c581abfc5','China','nova@sindbad.com','10-18 days','safety,industrial,gloves'),
  ('Organic cotton T-shirts','Apparel & Textiles','Customizable 100% organic cotton crew-neck T-shirts for private label programs.',4.80,200,8000,'photo-1521572163474-6864f9cf17ab','Turkey','atlas@sindbad.com','15-25 days','cotton,apparel,textile'),
  ('LED panel lights 60x60','Electronics','Energy-efficient commercial LED ceiling panels for offices and retail projects.',12.50,50,4500,'photo-1558008258-3256797b43f3','China','nova@sindbad.com','12-20 days','lighting,electrical,led'),
  ('Ceramic tableware set','Home & Kitchen','Modern glazed ceramic dinnerware for hospitality, wholesale and retail.',8.90,100,3000,'photo-1493106641515-6b5631de4bb9','Egypt','demo@sindbad.com','7-14 days','ceramic,kitchen,tableware'),
  ('Stainless steel water bottles','Sports & Outdoors','Double-wall vacuum insulated stainless steel bottles with custom branding.',3.40,300,9000,'photo-1602143407151-7111542de6e8','India','atlas@sindbad.com','18-28 days','bottle,sports,steel'),
  ('Premium dried dates','Food & Agriculture','Premium whole dried dates, export grade, available in bulk food-service packaging.',2.10,1000,25000,'photo-1601493700631-2b16ec4b4716','Egypt','demo@sindbad.com','5-10 days','dates,food,agriculture'),
  ('Corrugated shipping cartons','Packaging','Heavy-duty corrugated cartons with custom dimensions and printed branding.',0.42,2000,50000,'photo-1607082349566-187342175e2f','Turkey','atlas@sindbad.com','10-20 days','packaging,cartons,shipping'),
  ('Solar street lights','Electronics','Integrated solar LED street lights with high-efficiency panels and lithium battery.',39.00,30,1600,'photo-1509391366360-2e959784a276','China','nova@sindbad.com','20-35 days','solar,lighting,energy'),
  ('Commercial office chairs','Home & Kitchen','Ergonomic mesh office chairs for commercial fit-outs and bulk procurement.',42.00,20,900,'photo-150 cadeira','Turkey','atlas@sindbad.com','15-25 days','furniture,office,chair'),
  ('Reusable shopping bags','Packaging','Reusable non-woven shopping bags with custom logo printing.',0.38,3000,60000,'photo-1597481499666-130f8eb0a9','Egypt','demo@sindbad.com','7-12 days','bags,packaging,retail'),
  ('Industrial water pumps','Industrial Equipment','Heavy-duty centrifugal water pumps for agriculture and industrial facilities.',118.00,5,240,'photo- насос','China','nova@sindbad.com','25-40 days','pump,industrial,water'),
  ('Basmati rice bulk','Food & Agriculture','Long-grain premium basmati rice for distributors and food service buyers.',1.65,5000,80000,'photo-1586201375761-83865001e31c','India','atlas@sindbad.com','18-30 days','rice,food,grain'),
  ('Safety helmets EN-rated','Safety & PPE','Industrial protective helmets with adjustable suspension and ventilation.',3.10,300,10000,'photo-1504307651254-35680f356dfd','China','nova@sindbad.com','12-20 days','helmet,safety,ppe'),
  ('Cotton bed linen sets','Apparel & Textiles','Hotel-grade cotton bedding sets with multiple thread-count options.',18.50,100,1800,'photo-1631049307264-da0ec9d70304','Egypt','demo@sindbad.com','10-18 days','cotton,bedding,textile'),
  ('Aluminium profiles','Industrial Equipment','Precision aluminium extrusion profiles for construction and manufacturing.',2.85,1000,30000,'photo-1504917595217-d4dc5ebe6122','Turkey','atlas@sindbad.com','20-35 days','aluminium,construction,metal'),
  ('Bluetooth conference speaker','Electronics','Portable conference speakerphone with noise reduction for business meetings.',26.00,50,2100,'photo-1589903308904-1010c2294adc','China','nova@sindbad.com','15-25 days','audio,electronics,bluetooth'),
  ('Olive oil extra virgin','Food & Agriculture','Extra virgin olive oil, cold extracted, packed for wholesale export.',5.70,500,6000,'photo-1474979266404-7eaacbcd87c5','Egypt','demo@sindbad.com','7-15 days','olive,oil,food'),
  ('Sports resistance bands','Sports & Outdoors','Latex resistance band sets for fitness distributors and gyms.',2.20,500,12000,'photo-1598289431512-b97b0917affc','China','nova@sindbad.com','15-25 days','fitness,sports,training'),
  ('Glass food storage containers','Home & Kitchen','Borosilicate glass food containers with airtight lids for retail.',4.60,200,5000,'photo-1603199506016-b9a594b593c0','Turkey','atlas@sindbad.com','15-22 days','glass,kitchen,storage'),
  ('Kraft paper bags','Packaging','Recyclable kraft paper bags for retail, restaurants and branded packaging.',0.19,5000,100000,'photo-1607082348824-0a96f2a4b9da','Egypt','demo@sindbad.com','6-12 days','paper,packaging,eco'),
  ('Copper electrical cable','Electronics','PVC insulated copper cable for commercial electrical installations.',0.76,3000,70000,'photo-1558618666-fcd25c85cd64','China','nova@sindbad.com','20-30 days','cable,electrical,copper'),
  ('Leather safety work boots','Safety & PPE','Protective leather work boots with reinforced toe cap and anti-slip sole.',21.00,100,2500,'photo- boots','Turkey','atlas@sindbad.com','18-28 days','boots,safety,workwear'),
  ('Frozen strawberry IQF','Food & Agriculture','Individually quick frozen strawberries for food manufacturing and distributors.',2.80,1000,18000,'photo- frozen','Egypt','demo@sindbad.com','5-12 days','frozen,fruit,food'),
  ('Camping LED lantern','Sports & Outdoors','Rechargeable outdoor LED lantern for camping and emergency supply channels.',6.90,100,3500,'photo-1504851149312-7a075b496cc7','China','nova@sindbad.com','15-25 days','camping,outdoor,lighting')]
  for title,cat,desc,price,moq,stock,photo,origin,email,lead,tags in items:
   image=f'https://images.unsplash.com/{photo}?auto=format&fit=crop&w=900&q=80' if photo.startswith('photo-') and ' ' not in photo else 'https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=900&q=80'
   q.execute('INSERT INTO products(supplier_id,title,category,description,price,currency,moq,stock,image,origin,created_at,lead_time,tags) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(suppliers[email],title,cat,desc,price,'USD',moq,stock,image,origin,datetime.utcnow().isoformat(),lead,tags))
 suppliers={r['email']:r['id'] for r in q.execute("SELECT id,email FROM users WHERE role='supplier'").fetchall()}
 # Expanded catalogue: 96 additional curated demo listings across the existing categories.
 # This runs only for a fresh database; existing installations are upgraded additively below.
 c.commit()
 # For databases created by earlier versions, add missing catalogue entries without deleting user data.
 expanded = [
  ('Electronics', ['Industrial USB-C hubs','Wireless barcode scanners','Commercial Wi-Fi access points','24-port network switches','IP security camera systems','Smart energy meters','Portable SSD drives','Thermal receipt printers','Industrial touch monitors','Fiber optic patch cables','PoE network injectors','Rack-mount server cabinets'], [8.5,24,39,68,29,17,42,55,115,3.2,19,145], 'photo-1498049794561-7780e7231661', 'China', 'nova@sindbad.com', 'electronics,technology,wholesale'),
  ('Apparel & Textiles', ['Polyester sports polo shirts','Cotton hotel towels','Industrial workwear jackets','Denim fabric rolls','Non-woven medical gowns','Microfiber cleaning cloths','Knitted baby blankets','Linen table runners','Reflective safety vests','Canvas tote bags','Fleece hoodies','Hotel bathrobes'], [5.2,3.8,16,2.9,1.4,0.65,4.1,6.8,3.2,1.1,9.5,14], 'photo-1523381210434-271e8be1f52b', 'Turkey', 'atlas@sindbad.com', 'textile,apparel,fabric'),
  ('Home & Kitchen', ['Non-stick cookware sets','Stainless steel mixing bowls','Commercial food processors','Porcelain coffee mugs','Bamboo serving trays','Restaurant chef knives','Glass beverage dispensers','Stackable storage bins','LED desk lamps','Hotel mattress protectors','Air fryer accessories','Silicone baking moulds'], [28,4.5,89,1.2,3.4,8.8,12,2.1,7.5,6.4,3.6,1.9], 'photo-1556911220-e15b29be8c8f', 'Egypt', 'demo@sindbad.com', 'kitchen,home,household'),
  ('Food & Agriculture', ['Frozen mango chunks IQF','Raw cashew kernels','Arabica green coffee beans','Dried hibiscus flowers','Sesame seeds hulled','Frozen okra cuts','Tomato paste bulk cans','Red lentils wholesale','Natural honey bulk drums','Canned fava beans','Dehydrated onion flakes','Extra virgin olive oil bulk'], [2.6,7.9,6.2,3.1,1.8,1.4,1.2,1.3,4.7,0.9,2.2,5.4], 'photo-1542838132-92c53300491e', 'Egypt', 'demo@sindbad.com', 'food,agriculture,export'),
  ('Safety & PPE', ['Cut-resistant safety sleeves','Industrial safety goggles','Reusable respirator masks','High-visibility rain jackets','Chemical-resistant aprons','Ear protection earmuffs','Welding protective gloves','Fall arrest safety harnesses','Fire-resistant coveralls','First aid station kits','Safety face shields','Steel toe shoe covers'], [2.4,1.1,2.8,13,4.5,3.2,5.6,22,31,18,2.1,1.8], 'photo-1581092160562-40aa08e78837', 'China', 'nova@sindbad.com', 'safety,ppe,industrial'),
  ('Sports & Outdoors', ['Adjustable dumbbell sets','Yoga exercise mats','Camping sleeping bags','Outdoor folding chairs','Insulated cooler boxes','Fitness jump ropes','Professional footballs','Cycling helmets','Trekking poles pairs','Resistance training tubes','Waterproof dry bags','Portable camping tables'], [34,5.4,18,12,16,1.8,7.5,11,8.2,2.9,4.6,21], 'photo-1517649763962-0c623066013b', 'China', 'nova@sindbad.com', 'sports,outdoor,fitness'),
  ('Packaging', ['Stretch wrapping film rolls','Biodegradable mailer bags','PET plastic bottles','Aluminium food containers','Printed folding cartons','Bubble cushioning rolls','Jute shopping sacks','Zip-lock packaging pouches','Paper honeycomb wrap','Plastic pallet corner guards','Tamper-evident labels','Vacuum sealing bags'], [8.2,0.12,0.08,0.06,0.22,5.1,0.45,0.04,3.8,0.3,0.015,0.035], 'photo-1607082349566-187342175e2f', 'Turkey', 'atlas@sindbad.com', 'packaging,shipping,wholesale'),
  ('Industrial Equipment', ['Air compressor 50L','Centrifugal water pump 2HP','Industrial electric motors','Hydraulic hose assemblies','Pneumatic control valves','Stainless steel pipe fittings','Welding inverter machines','Industrial conveyor rollers','Diesel generator 20kVA','Bearing kits assorted','Pressure gauge sets','Workshop hydraulic jacks'], [185,145,210,8.5,16,3.2,95,12,1850,2.4,6.5,78], 'photo-1581092921461-eab62e97a780', 'China', 'nova@sindbad.com', 'industrial,machinery,equipment'),
 ]
 photo_fallback='https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=900&q=80'
 for cat,names,prices,photo,origin,email,tags in expanded:
  for i,title in enumerate(names):
   if q.execute('SELECT 1 FROM products WHERE title=?',(title,)).fetchone():
    continue
   supplier_id=suppliers[email]
   moq=[50,100,200,500,1000,25,300,100][i%8]
   stock=[1800,3500,7000,12000,24000,900,5200,15000][i%8]
   lead=['7-14 days','10-18 days','12-20 days','15-25 days'][i%4]
   desc=f'{title} supplied for distributors, importers and commercial procurement. Bulk order options, export packing and supplier quotation available.'
   image=f'https://images.unsplash.com/{photo}?auto=format&fit=crop&w=900&q=80'
   q.execute('INSERT INTO products(supplier_id,title,category,description,price,currency,moq,stock,image,origin,created_at,lead_time,tags) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(supplier_id,title,cat,desc,prices[i],'USD',moq,stock,image,origin,datetime.utcnow().isoformat(),lead,tags))
 c.commit(); c.close()
init_db()

@app.get('/')
def home():return FileResponse(os.path.join(BASE,'static','index.html'))
@app.get('/api/health')
def health():return {'status':'ok','service':'Sindbad','version':'2.0.0'}
@app.post('/api/register')
def register(x:Register,response:Response):
 if x.role not in ('buyer','supplier'):raise HTTPException(400,'Choose buyer or supplier')
 salt=secrets.token_hex(16); c=db()
 try:
  cur=c.execute('INSERT INTO users(name,email,salt,password_hash,role,company,country,created_at) VALUES(?,?,?,?,?,?,?,?)',(x.name,x.email.lower(),salt,pw_hash(x.password,salt),x.role,x.company,x.country,datetime.utcnow().isoformat())); c.commit(); uid=cur.lastrowid
 except sqlite3.IntegrityError:c.close();raise HTTPException(409,'An account with this email already exists')
 c.close();response.set_cookie('sindbad_session',token_for(uid),httponly=True,samesite='lax',max_age=604800);return {'ok':True,'user':user_by_id(uid)}
@app.post('/api/login')
def login(x:Login,response:Response):
 c=db();u=c.execute('SELECT * FROM users WHERE email=?',(x.email.lower(),)).fetchone();c.close()
 if not u or not hmac.compare_digest(pw_hash(x.password,u['salt']),u['password_hash']):raise HTTPException(401,'Email or password is incorrect')
 response.set_cookie('sindbad_session',token_for(u['id']),httponly=True,samesite='lax',max_age=604800);return {'ok':True,'user':user_by_id(u['id'])}
@app.post('/api/logout')
def logout(response:Response):response.delete_cookie('sindbad_session');return {'ok':True}
@app.get('/api/me')
def me(request:Request):return {'user':current_user(request)}
@app.get('/api/products')
def products(q:str='',category:str='',sort:str='new',min_price:float|None=None,max_price:float|None=None,origin:str='',limit:int=200):
 c=db();sql='''SELECT p.*,u.company supplier_company,u.country supplier_country,u.name supplier_name FROM products p JOIN users u ON u.id=p.supplier_id WHERE p.active=1''';args=[]
 if q:sql+=' AND (p.title LIKE ? OR p.description LIKE ? OR p.category LIKE ? OR p.tags LIKE ? OR u.company LIKE ? OR u.name LIKE ? OR u.country LIKE ?)';args += [f'%{q}%']*7
 if category:sql+=' AND p.category=?';args.append(category)
 if origin:sql+=' AND p.origin=?';args.append(origin)
 if min_price is not None:sql+=' AND p.price>=?';args.append(min_price)
 if max_price is not None:sql+=' AND p.price<=?';args.append(max_price)
 sql+=' ORDER BY '+({'price_asc':'p.price ASC','price_desc':'p.price DESC','popular':'p.id DESC','new':'p.id DESC'}.get(sort,'p.id DESC'))+' LIMIT ?';args.append(min(max(limit,1),200));rows=[dict(r) for r in c.execute(sql,args).fetchall()];c.close();return rows
@app.get('/api/products/{pid}')
def product_detail(pid:int,request:Request):
 c=db();r=c.execute('SELECT p.*,u.company supplier_company,u.country supplier_country,u.name supplier_name,u.id supplier_user_id FROM products p JOIN users u ON u.id=p.supplier_id WHERE p.id=? AND p.active=1',(pid,)).fetchone();c.close()
 if not r:raise HTTPException(404,'Product not found')
 u=current_user(request)
 if u:
  c=db();c.execute('INSERT INTO interactions(user_id,product_id,event_type,created_at) VALUES(?,?,?,?)',(u['id'],pid,'view',datetime.utcnow().isoformat()));c.commit();c.close()
 return dict(r)
@app.get('/api/categories')
def categories():
 c=db();rows=[dict(r) for r in c.execute('SELECT category,COUNT(*) product_count FROM products WHERE active=1 GROUP BY category ORDER BY category').fetchall()];c.close();return rows
@app.get('/api/suppliers')
def suppliers(q:str=''):
 c=db();sql="SELECT u.id,u.name,u.company,u.country,COUNT(p.id) product_count FROM users u LEFT JOIN products p ON p.supplier_id=u.id AND p.active=1 WHERE u.role='supplier'";args=[]
 if q:sql+=' AND (u.company LIKE ? OR u.country LIKE ?)';args=[f'%{q}%']*2
 sql+=' GROUP BY u.id ORDER BY product_count DESC';rows=[dict(r) for r in c.execute(sql,args).fetchall()];c.close();return rows
@app.post('/api/products')
def add_product(x:ProductIn,u=Depends(require_user)):
 if u['role']!='supplier':raise HTTPException(403,'Supplier account required')
 c=db();cur=c.execute('INSERT INTO products(supplier_id,title,category,description,price,currency,moq,stock,image,origin,created_at,lead_time,tags) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(u['id'],x.title,x.category,x.description,x.price,x.currency,x.moq,x.stock,x.image,x.origin or u['country'],datetime.utcnow().isoformat(),x.lead_time,x.tags));c.commit();pid=cur.lastrowid;c.close();return {'ok':True,'id':pid}
@app.put('/api/products/{pid}')
def update_product(pid:int,x:ProductIn,u=Depends(require_user)):
 c=db();p=c.execute('SELECT supplier_id FROM products WHERE id=?',(pid,)).fetchone()
 if not p:c.close();raise HTTPException(404,'Product not found')
 if p['supplier_id']!=u['id']:c.close();raise HTTPException(403,'You can only edit your own products')
 c.execute('UPDATE products SET title=?,category=?,description=?,price=?,currency=?,moq=?,stock=?,image=?,origin=?,lead_time=?,tags=? WHERE id=?',(x.title,x.category,x.description,x.price,x.currency,x.moq,x.stock,x.image,x.origin,x.lead_time,x.tags,pid));c.commit();c.close();return {'ok':True}
@app.delete('/api/products/{pid}')
def delete_product(pid:int,u=Depends(require_user)):
 c=db();cur=c.execute('UPDATE products SET active=0 WHERE id=? AND supplier_id=?',(pid,u['id']));c.commit();c.close()
 if not cur.rowcount:raise HTTPException(404,'Product not found')
 return {'ok':True}
@app.post('/api/interactions')
def track_event(x:EventIn,u=Depends(require_user)):
 if x.event_type not in ('view','click','cart','purchase','favorite'):raise HTTPException(400,'Unsupported interaction')
 c=db();exists=c.execute('SELECT id FROM products WHERE id=? AND active=1',(x.product_id,)).fetchone()
 if not exists:c.close();raise HTTPException(404,'Product not found')
 c.execute('INSERT INTO interactions(user_id,product_id,event_type,created_at) VALUES(?,?,?,?)',(u['id'],x.product_id,x.event_type,datetime.utcnow().isoformat()));c.commit();c.close();return {'ok':True}
@app.get('/api/recommendations')
def recommendations(request:Request,limit:int=12):
    """Hybrid recommendations: content affinity + user-user CF + popularity cold-start."""
    import math
    u=current_user(request); c=db()
    allp=[dict(r) for r in c.execute('''SELECT p.*,u.company supplier_company,u.country supplier_country FROM products p JOIN users u ON u.id=p.supplier_id WHERE p.active=1 AND p.stock>0''').fetchall()]
    if not allp:
        c.close(); return {'items':[],'strategy':'empty_catalog','model':'hybrid-v2'}
    by_id={p['id']:p for p in allp}; weights={'view':1.0,'click':1.7,'cart':3.5,'favorite':4.0,'purchase':5.0}
    scores={p['id']:0.0 for p in allp}; reasons={}; strategies=[]
    # Popularity prior, also used for anonymous/new buyers (cold start).
    pop_rows=c.execute("SELECT product_id, SUM(CASE event_type WHEN 'purchase' THEN 5 WHEN 'cart' THEN 3.5 WHEN 'favorite' THEN 4 ELSE 1 END) score FROM interactions GROUP BY product_id").fetchall()
    fav_rows=c.execute('SELECT product_id,COUNT(*) n FROM favorites GROUP BY product_id').fetchall()
    for r in pop_rows:
        if r['product_id'] in scores: scores[r['product_id']]+=float(r['score'])*0.25
    for r in fav_rows:
        if r['product_id'] in scores: scores[r['product_id']]+=float(r['n'])*0.5
    # A mild catalog prior avoids identical ties in a brand-new marketplace without inventing user events.
    for p in allp: scores[p['id']]+=0.05*(1.0/(1.0+max(0,p['price'])))
    if u:
        own_rows=c.execute('SELECT product_id,event_type,COUNT(*) n FROM interactions WHERE user_id=? GROUP BY product_id,event_type',(u['id'],)).fetchall()
        own_vec={}; category_affinity={}; tag_affinity={}; own_seen=set()
        for r in own_rows:
            pid=r['product_id']; w=weights.get(r['event_type'],1.0)*r['n']; own_vec[pid]=own_vec.get(pid,0)+w; own_seen.add(pid)
            product=by_id.get(pid)
            if product:
                category_affinity[product['category']]=category_affinity.get(product['category'],0)+w
                for tag in (product.get('tags') or '').lower().split(','):
                    tag=tag.strip()
                    if tag: tag_affinity[tag]=tag_affinity.get(tag,0)+w*0.25
        favs=c.execute('SELECT product_id FROM favorites WHERE user_id=?',(u['id'],)).fetchall()
        for f in favs:
            pid=f['product_id']; own_seen.add(pid); own_vec[pid]=own_vec.get(pid,0)+4.0
            product=by_id.get(pid)
            if product: category_affinity[product['category']]=category_affinity.get(product['category'],0)+4.0
        if own_seen: strategies.append('content_based')
        # Content similarity: category + shared tags + product attributes.
        for p in allp:
            if p['id'] in own_seen: continue
            cat_score=category_affinity.get(p['category'],0)
            tags=(p.get('tags') or '').lower().split(',')
            tag_score=sum(tag_affinity.get(t.strip(),0) for t in tags if t.strip())
            if cat_score or tag_score:
                scores[p['id']]+=cat_score*0.85+tag_score*0.7
                reasons[p['id']]='Based on categories and product tags you explored'
        # Correct user-user collaborative filtering using weighted cosine similarity.
        other_rows=c.execute('SELECT user_id,product_id,event_type,COUNT(*) n FROM interactions WHERE user_id<>? GROUP BY user_id,product_id,event_type',(u['id'],)).fetchall()
        user_vectors={}
        for r in other_rows:
            pid=r['product_id']
            if pid not in by_id: continue
            vec=user_vectors.setdefault(r['user_id'],{})
            vec[pid]=vec.get(pid,0)+weights.get(r['event_type'],1.0)*r['n']
        similarities=[]
        own_norm=math.sqrt(sum(v*v for v in own_vec.values())) if own_vec else 0.0
        if own_vec and own_norm:
            for other_id,vec in user_vectors.items():
                dot=sum(v*vec.get(pid,0) for pid,v in own_vec.items())
                other_norm=math.sqrt(sum(v*v for v in vec.values()))
                sim=dot/(own_norm*other_norm) if other_norm else 0.0
                if sim>0: similarities.append((sim,vec))
        for sim,vec in sorted(similarities,key=lambda x:x[0],reverse=True)[:40]:
            for pid,engagement in vec.items():
                if pid not in own_seen and pid in scores:
                    scores[pid]+=sim*engagement*1.15
                    reasons[pid]='Popular with buyers who have similar sourcing activity'
        if similarities: strategies.append('collaborative_filtering')
    if not strategies: strategies=['popularity_cold_start']
    ranked=sorted(allp,key=lambda p:(scores[p['id']],p['id']),reverse=True)
    # Diversify the first page by supplier/category where possible.
    chosen=[]; supplier_counts={}; category_counts={}
    for p in ranked:
        if len(chosen)>=min(max(limit,1),30): break
        if supplier_counts.get(p['supplier_id'],0)>=5 or category_counts.get(p['category'],0)>=5: continue
        chosen.append(p); supplier_counts[p['supplier_id']]=supplier_counts.get(p['supplier_id'],0)+1; category_counts[p['category']]=category_counts.get(p['category'],0)+1
    for p in chosen:
        p['recommendation_score']=round(scores[p['id']],4)
        p['recommendation_reason']=reasons.get(p['id'],'Popular wholesale choice for new buyers')
        p['recommendation_model']='+'.join(strategies)
    c.close()
    return {'items':chosen,'strategy':strategies,'model':'hybrid-v2','personalized':bool(u and (own_vec if u else False))}

@app.get('/api/favorites')
def get_favorites(u=Depends(require_user)):
 c=db();rows=[dict(r) for r in c.execute('SELECT p.*,u.company supplier_company,u.country supplier_country FROM favorites f JOIN products p ON p.id=f.product_id JOIN users u ON u.id=p.supplier_id WHERE f.user_id=? ORDER BY f.created_at DESC',(u['id'],)).fetchall()];c.close();return rows
@app.post('/api/favorites/{pid}')
def toggle_favorite(pid:int,u=Depends(require_user)):
 c=db();exists=c.execute('SELECT 1 FROM favorites WHERE user_id=? AND product_id=?',(u['id'],pid)).fetchone()
 if exists:c.execute('DELETE FROM favorites WHERE user_id=? AND product_id=?',(u['id'],pid));saved=False
 else:
  if not c.execute('SELECT 1 FROM products WHERE id=? AND active=1',(pid,)).fetchone():c.close();raise HTTPException(404,'Product not found')
  c.execute('INSERT INTO favorites(user_id,product_id,created_at) VALUES(?,?,?)',(u['id'],pid,datetime.utcnow().isoformat()));saved=True
  c.execute('INSERT INTO interactions(user_id,product_id,event_type,created_at) VALUES(?,?,?,?)',(u['id'],pid,'favorite',datetime.utcnow().isoformat()))
 c.commit();c.close();return {'ok':True,'saved':saved}
@app.post('/api/orders')
def create_order(x:OrderIn,u=Depends(require_user)):
 if u['role']!='buyer':raise HTTPException(403,'Buyer account required')
 if not x.items:raise HTTPException(400,'Your cart is empty')
 c=db();total=0;normalized=[]
 try:
  for item in x.items:
   p=c.execute('SELECT id,title,price,currency,moq,stock,supplier_id FROM products WHERE id=? AND active=1',(item.product_id,)).fetchone();qty=item.quantity
   if not p or qty<p['moq'] or qty>p['stock']:raise HTTPException(400,'Product unavailable or quantity is below MOQ / above stock')
   total+=p['price']*qty;normalized.append({'product_id':p['id'],'title':p['title'],'quantity':qty,'unit_price':p['price'],'currency':p['currency'],'supplier_id':p['supplier_id']})
  cur=c.execute('INSERT INTO orders(buyer_id,total,currency,status,items_json,created_at) VALUES(?,?,?,?,?,?)',(u['id'],total,'USD','pending',json.dumps(normalized),datetime.utcnow().isoformat()));oid=cur.lastrowid
  for item in normalized:
   stock_update=c.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',(item['quantity'],item['product_id'],item['quantity']))
   if stock_update.rowcount != 1: raise HTTPException(409,'Stock changed while placing your order; please refresh the cart')
   c.execute('INSERT INTO interactions(user_id,product_id,event_type,created_at) VALUES(?,?,?,?)',(u['id'],item['product_id'],'purchase',datetime.utcnow().isoformat()))
  c.commit()
 except Exception:c.rollback();c.close();raise
 c.close();return {'ok':True,'order_id':oid,'total':round(total,2),'status':'pending','note':'Demo order only. No payment was collected.'}
@app.get('/api/orders')
def orders(u=Depends(require_user)):
 c=db()
 if u['role']=='buyer':rows=c.execute('SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC',(u['id'],)).fetchall()
 else:rows=c.execute('SELECT DISTINCT o.* FROM orders o JOIN json_each(o.items_json) j WHERE json_extract(j.value,"$.supplier_id")=? ORDER BY o.id DESC',(u['id'],)).fetchall()
 out=[]
 for r in rows:d=dict(r);d['items']=json.loads(d.pop('items_json'));out.append(d)
 c.close();return out
@app.post('/api/rfqs')
def create_rfq(x:RFQIn,u=Depends(require_user)):
 if u['role']!='buyer':raise HTTPException(403,'Buyer account required')
 c=db();cur=c.execute('INSERT INTO rfqs(buyer_id,title,details,quantity,target_price,destination,created_at) VALUES(?,?,?,?,?,?,?)',(u['id'],x.title,x.details,x.quantity,x.target_price,x.destination,datetime.utcnow().isoformat()));c.commit();rid=cur.lastrowid;c.close();return {'ok':True,'id':rid}
@app.get('/api/rfqs')
def rfqs(u=Depends(require_user)):
 c=db()
 if u['role']=='buyer':rows=c.execute('SELECT r.*,u.company buyer_company FROM rfqs r JOIN users u ON u.id=r.buyer_id WHERE r.buyer_id=? ORDER BY r.id DESC',(u['id'],)).fetchall()
 else:rows=c.execute("SELECT r.*,u.company buyer_company,(SELECT COUNT(*) FROM quotations q WHERE q.rfq_id=r.id) quote_count FROM rfqs r JOIN users u ON u.id=r.buyer_id WHERE r.status='open' ORDER BY r.id DESC").fetchall()
 c.close();return [dict(r) for r in rows]
@app.get('/api/dashboard')
def dashboard(u=Depends(require_user)):
 c=db()
 if u['role']=='supplier':
  stats={'products':c.execute('SELECT COUNT(*) n FROM products WHERE supplier_id=? AND active=1',(u['id'],)).fetchone()['n'],'orders':c.execute('SELECT COUNT(DISTINCT o.id) n FROM orders o,json_each(o.items_json) j WHERE json_extract(j.value,"$.supplier_id")=?',(u['id'],)).fetchone()['n'],'favorites':c.execute('SELECT COUNT(*) n FROM favorites f JOIN products p ON p.id=f.product_id WHERE p.supplier_id=?',(u['id'],)).fetchone()['n']}
 else:stats={'orders':c.execute('SELECT COUNT(*) n FROM orders WHERE buyer_id=?',(u['id'],)).fetchone()['n'],'rfqs':c.execute('SELECT COUNT(*) n FROM rfqs WHERE buyer_id=?',(u['id'],)).fetchone()['n'],'favorites':c.execute('SELECT COUNT(*) n FROM favorites WHERE user_id=?',(u['id'],)).fetchone()['n']}
 c.close();return {'user':u,'stats':stats}


@app.get('/api/supplier/products')
def supplier_products(u=Depends(require_user)):
 if u['role']!='supplier':raise HTTPException(403,'Supplier account required')
 c=db();rows=[dict(r) for r in c.execute('SELECT * FROM products WHERE supplier_id=? AND active=1 ORDER BY id DESC',(u['id'],)).fetchall()];c.close();return rows

class QuoteIn(BaseModel):
 price:float=Field(gt=0);currency:str='USD';lead_time:str='7-15 days';notes:str=''

@app.post('/api/rfqs/{rfq_id}/quotes')
def submit_quote(rfq_id:int,x:QuoteIn,u=Depends(require_user)):
 if u['role']!='supplier':raise HTTPException(403,'Supplier account required')
 c=db();rfq=c.execute("SELECT id FROM rfqs WHERE id=? AND status='open'",(rfq_id,)).fetchone()
 if not rfq:c.close();raise HTTPException(404,'Open RFQ not found')
 try:
  cur=c.execute('INSERT INTO quotations(rfq_id,supplier_id,price,currency,lead_time,notes,created_at) VALUES(?,?,?,?,?,?,?)',(rfq_id,u['id'],x.price,x.currency,x.lead_time,x.notes,datetime.utcnow().isoformat()));c.commit();qid=cur.lastrowid
 except sqlite3.IntegrityError:c.close();raise HTTPException(409,'You already submitted a quotation for this request')
 c.close();return {'ok':True,'quote_id':qid}

@app.get('/api/rfqs/{rfq_id}/quotes')
def list_quotes(rfq_id:int,u=Depends(require_user)):
 c=db();rfq=c.execute('SELECT buyer_id FROM rfqs WHERE id=?',(rfq_id,)).fetchone()
 if not rfq:c.close();raise HTTPException(404,'RFQ not found')
 if u['role']=='buyer' and rfq['buyer_id']!=u['id']:c.close();raise HTTPException(403,'This request does not belong to your account')
 rows=[dict(r) for r in c.execute('SELECT q.id,q.rfq_id,q.price,q.currency,q.lead_time,q.notes,q.created_at,u.company supplier_company,u.country supplier_country FROM quotations q JOIN users u ON u.id=q.supplier_id WHERE q.rfq_id=? ORDER BY q.price ASC',(rfq_id,)).fetchall()];c.close();return rows
