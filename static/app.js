/* Sindbad 2.0 - bilingual SPA over the FastAPI backend */
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={user:null,lang:localStorage.getItem('sb_lang')||'en',cart:JSON.parse(localStorage.getItem('sb_cart')||'[]'),products:[],favIds:new Set()};

const I18N={
en:{tagline:'Global B2B Marketplace',navMarket:'Marketplace',navSuppliers:'Suppliers',navRfqs:'Buying requests',navDashboard:'Dashboard',signIn:'Sign in',signOut:'Sign out',
heroTitle:'Source wholesale products from suppliers worldwide',heroSub:'A bilingual B2B sourcing marketplace with RFQs, quotations and AI-powered recommendations.',
recoTitle:'Recommended for you',searchPh:'Search products, suppliers, tags...',allCategories:'All categories',allOrigins:'All origins',minPrice:'Min $',maxPrice:'Max $',
sortNew:'Newest',sortPriceAsc:'Price: low to high',sortPriceDesc:'Price: high to low',noProducts:'No products match these filters.',
suppliersTitle:'Supplier directory',supplierSearchPh:'Search by company or country...',products:'products',
rfqBuyerTitle:'My buying requests',rfqSupplierTitle:'Open buying requests',rfqAnon:'Sign in to publish buying requests or submit quotations.',
rfqTitlePh:'What do you want to source?',rfqDetailsPh:'Specifications, packaging, certifications...',rfqQtyPh:'Quantity',rfqTargetPh:'Target price (optional)',rfqDestPh:'Destination (optional)',rfqPublish:'Publish request',
dashTitle:'Dashboard',dashOrders:'Orders',dashFavorites:'Favorites',myProducts:'My products',dashAnon:'Sign in to see your dashboard.',
pTitlePh:'Product title',pCategoryPh:'Category',pPricePh:'Unit price (USD)',pMoqPh:'MOQ',pStockPh:'Stock',pOriginPh:'Origin country',pLeadPh:'Lead time (e.g. 7-15 days)',pTagsPh:'Tags, comma separated',pImagePh:'Image URL (optional)',pDescPh:'Description',pSave:'Save product',pCancel:'Cancel edit',
tabLogin:'Sign in',tabRegister:'Create account',emailPh:'Email',passPh:'Password (8+ chars)',namePh:'Full name',companyPh:'Company',countryPh:'Country',roleBuyer:'Buyer',roleSupplier:'Supplier',
demoHint:'Demo: demo@sindbad.com / demo1234 (supplier), buyer@sindbad.com / buyer1234 (buyer)',
cartTitle:'Sourcing cart',cartEmpty:'Your cart is empty.',checkout:'Place demo order',total:'Total',moq:'MOQ',stock:'in stock',addCart:'Add to cart',details:'Details',
orderOk:'Demo order placed. No payment was collected.',needBuyer:'A buyer account is required.',needSupplier:'A supplier account is required.',needAuth:'Please sign in first.',
quotesFor:'Quotations for',noQuotes:'No quotations yet.',best:'Best price',submitQuote:'Submit quotation',pricePh:'Your price (USD)',leadPh:'Lead time',notesPh:'Notes (optional)',quoteOk:'Quotation submitted.',
rfqOk:'Buying request published.',qty:'Qty',edit:'Edit',remove:'Delete',viewQuotes:'Compare quotes',close:'Close',from:'from',ordersEmpty:'No orders yet.',favsEmpty:'No favorites yet.',productsEmpty:'No products yet.',rfqsEmpty:'No requests yet.',langBtn:'عربي'},
ar:{tagline:'سوق عالمي بين الشركات',navMarket:'السوق',navSuppliers:'الموردون',navRfqs:'طلبات الشراء',navDashboard:'لوحة التحكم',signIn:'تسجيل الدخول',signOut:'تسجيل الخروج',
heroTitle:'استورد منتجات الجملة من موردين حول العالم',heroSub:'سوق B2B ثنائي اللغة مع طلبات تسعير وعروض وتوصيات ذكية.',
recoTitle:'مقترح لك',searchPh:'ابحث عن منتجات أو موردين أو كلمات...',allCategories:'كل الفئات',allOrigins:'كل البلدان',minPrice:'أقل $',maxPrice:'أعلى $',
sortNew:'الأحدث',sortPriceAsc:'السعر: من الأقل',sortPriceDesc:'السعر: من الأعلى',noProducts:'لا توجد منتجات مطابقة.',
suppliersTitle:'دليل الموردين',supplierSearchPh:'ابحث بالشركة أو البلد...',products:'منتج',
rfqBuyerTitle:'طلبات الشراء الخاصة بي',rfqSupplierTitle:'طلبات الشراء المفتوحة',rfqAnon:'سجل الدخول لنشر طلبات الشراء أو تقديم عروض الأسعار.',
rfqTitlePh:'ما الذي تريد استيراده؟',rfqDetailsPh:'المواصفات، التغليف، الشهادات...',rfqQtyPh:'الكمية',rfqTargetPh:'السعر المستهدف (اختياري)',rfqDestPh:'جهة الشحن (اختياري)',rfqPublish:'انشر الطلب',
dashTitle:'لوحة التحكم',dashOrders:'الطلبات',dashFavorites:'المفضلة',myProducts:'منتجاتي',dashAnon:'سجل الدخول لرؤية لوحة التحكم.',
pTitlePh:'اسم المنتج',pCategoryPh:'الفئة',pPricePh:'سعر الوحدة (دولار)',pMoqPh:'أقل كمية',pStockPh:'المخزون',pOriginPh:'بلد المنشأ',pLeadPh:'مدة التوريد (مثال: 7-15 يوم)',pTagsPh:'كلمات مفتاحية مفصولة بفواصل',pImagePh:'رابط الصورة (اختياري)',pDescPh:'الوصف',pSave:'حفظ المنتج',pCancel:'إلغاء التعديل',
tabLogin:'تسجيل الدخول',tabRegister:'إنشاء حساب',emailPh:'البريد الإلكتروني',passPh:'كلمة المرور (8+ أحرف)',namePh:'الاسم الكامل',companyPh:'الشركة',countryPh:'البلد',roleBuyer:'مشتري',roleSupplier:'مورد',
demoHint:'تجريبي: demo@sindbad.com / demo1234 (مورد)، buyer@sindbad.com / buyer1234 (مشتري)',
cartTitle:'سلة التوريد',cartEmpty:'سلتك فارغة.',checkout:'تأكيد الطلب التجريبي',total:'الإجمالي',moq:'أقل كمية',stock:'في المخزون',addCart:'أضف للسلة',details:'التفاصيل',
orderOk:'تم تسجيل الطلب التجريبي. لم يتم تحصيل أي مبلغ.',needBuyer:'يلزم حساب مشتري.',needSupplier:'يلزم حساب مورد.',needAuth:'سجل الدخول أولاً.',
quotesFor:'عروض الأسعار لـ',noQuotes:'لا توجد عروض بعد.',best:'أفضل سعر',submitQuote:'قدم عرض سعر',pricePh:'سعرك (دولار)',leadPh:'مدة التوريد',notesPh:'ملاحظات (اختياري)',quoteOk:'تم إرسال عرض السعر.',
rfqOk:'تم نشر طلب الشراء.',qty:'الكمية',edit:'تعديل',remove:'حذف',viewQuotes:'قارن العروض',close:'إغلاق',from:'من',ordersEmpty:'لا توجد طلبات بعد.',favsEmpty:'لا توجد مفضلات بعد.',productsEmpty:'لا توجد منتجات بعد.',rfqsEmpty:'لا توجد طلبات بعد.',langBtn:'English'}
};
const t=k=>(I18N[state.lang]&&I18N[state.lang][k])||I18N.en[k]||k;

function applyLang(){
  const ar=state.lang==='ar';
  document.documentElement.lang=state.lang;
  document.documentElement.dir=ar?'rtl':'ltr';
  document.body.classList.toggle('rtl',ar);
  $('#langToggle').textContent=t('langBtn');
  $$('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));
  $$('[data-i18n-ph]').forEach(el=>el.placeholder=t(el.dataset.i18nPh));
  renderAll();
}

async function api(path,opts={}){
  if(opts.body){opts.headers={'content-type':'application/json'};opts.body=JSON.stringify(opts.body);}
  const r=await fetch(path,opts);
  const d=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(d.detail||('Error '+r.status));
  return d;
}
function toast(msg,err){const el=document.createElement('div');el.className='toast'+(err?' err':'');el.textContent=msg;$('#toasts').appendChild(el);setTimeout(()=>el.remove(),3600);}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>'$'+Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});

/* ---------- views ---------- */
function show(view){
  $$('.view').forEach(v=>v.classList.add('hidden'));
  $('#view-'+view).classList.remove('hidden');
  $$('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
  if(view==='rfqs')renderRfqs();
  if(view==='dashboard')renderDashboard();
}
$$('.nav-btn').forEach(b=>b.onclick=()=>show(b.dataset.view));
$('#brand').onclick=()=>show('market');

/* ---------- auth ---------- */
function renderAuth(){
  const u=state.user;
  $('#userChip').classList.toggle('hidden',!u);
  if(u)$('#userChip').textContent=u.company+' · '+(u.role==='buyer'?t('roleBuyer'):t('roleSupplier'));
  $('#authBtn').textContent=u?t('signOut'):t('signIn');
}
$('#authBtn').onclick=async()=>{
  if(state.user){await api('/api/logout',{method:'POST'});state.user=null;state.favIds=new Set();renderAuth();renderAll();return;}
  openModal('authModal');
};
$('#tabLogin').onclick=()=>{$('#tabLogin').classList.add('active');$('#tabRegister').classList.remove('active');$('#loginForm').classList.remove('hidden');$('#registerForm').classList.add('hidden');};
$('#tabRegister').onclick=()=>{$('#tabRegister').classList.add('active');$('#tabLogin').classList.remove('active');$('#registerForm').classList.remove('hidden');$('#loginForm').classList.add('hidden');};
$('#loginForm').onsubmit=async e=>{
  e.preventDefault();
  try{
    const d=await api('/api/login',{method:'POST',body:{email:$('#liEmail').value,password:$('#liPass').value}});
    state.user=d.user;closeModal('authModal');renderAuth();await afterAuth();
  }catch(err){toast(err.message,true);}
};
$('#registerForm').onsubmit=async e=>{
  e.preventDefault();
  try{
    const d=await api('/api/register',{method:'POST',body:{name:$('#rgName').value,email:$('#rgEmail').value,password:$('#rgPass').value,company:$('#rgCompany').value,country:$('#rgCountry').value,role:$('#rgRole').value}});
    state.user=d.user;closeModal('authModal');renderAuth();await afterAuth();
  }catch(err){toast(err.message,true);}
};
async function afterAuth(){
  if(state.user&&state.user.role==='buyer'){
    try{const favs=await api('/api/favorites');state.favIds=new Set(favs.map(f=>f.id));}catch(e){}
  }
  renderAll();
}

/* ---------- products ---------- */
async function loadProducts(){
  const p=new URLSearchParams();
  const q=$('#fSearch').value.trim();if(q)p.set('q',q);
  if($('#fCategory').value)p.set('category',$('#fCategory').value);
  if($('#fOrigin').value)p.set('origin',$('#fOrigin').value);
  if($('#fMin').value)p.set('min_price',$('#fMin').value);
  if($('#fMax').value)p.set('max_price',$('#fMax').value);
  p.set('sort',$('#fSort').value);
  state.products=await api('/api/products?'+p);
  renderProducts();
}
function card(p){
  const fav=state.favIds.has(p.id);
  const tags=(p.tags||'').split(',').map(x=>x.trim()).filter(Boolean).slice(0,3).map(x=>`<span class="chip">${esc(x)}</span>`).join('');
  return `<article class="card">
    <img src="${esc(p.image)}" alt="${esc(p.title)}" loading="lazy" onerror="this.style.display='none'">
    <div class="card-body">
      <div class="card-title">${esc(p.title)}</div>
      <div class="card-meta">${esc(p.supplier_company||'')} · ${esc(p.origin||'')}</div>
      <div class="card-price">${money(p.price)} <span class="card-meta">/ ${t('moq')} ${p.moq}</span></div>
      <div class="card-tags">${tags}</div>
      <div class="card-actions">
        <button class="primary-btn" onclick="openProduct(${p.id})">${t('details')}</button>
        <button class="ghost-btn fav-btn ${fav?'active':''}" onclick="toggleFav(${p.id},this)">${fav?'★':'☆'}</button>
      </div>
    </div>
  </article>`;
}
function renderProducts(){
  $('#productGrid').innerHTML=state.products.map(card).join('');
  $('#marketEmpty').classList.toggle('hidden',state.products.length>0);
}
async function loadFilters(){
  const cats=await api('/api/categories');
  const catSel=$('#fCategory');const keep=catSel.value;
  catSel.innerHTML=`<option value="">${t('allCategories')}</option>`+cats.map(c=>`<option ${c.category===keep?'selected':''} value="${esc(c.category)}">${esc(c.category)} (${c.product_count})</option>`).join('');
  const origins=[...new Set(state.products.map(p=>p.origin).filter(Boolean))].sort();
  const oSel=$('#fOrigin');const oKeep=oSel.value;
  oSel.innerHTML=`<option value="">${t('allOrigins')}</option>`+origins.map(o=>`<option ${o===oKeep?'selected':''}>${esc(o)}</option>`).join('');
}
let deb;['fSearch','fCategory','fOrigin','fMin','fMax','fSort'].forEach(id=>$('#'+id).addEventListener('input',()=>{clearTimeout(deb);deb=setTimeout(loadProducts,350);}));

async function loadRecos(){
  try{
    const d=await api('/api/recommendations?limit=12');
    if(!d.items||!d.items.length)return;
    $('#recoWrap').classList.remove('hidden');
    $('#recoStrategy').textContent=d.model+(d.personalized?' · '+t('recoTitle'):'');
    $('#recoRow').innerHTML=d.items.map(p=>card(p).replace('</article>',`<div class="reco-reason" style="padding:0 14px 12px">${esc(p.recommendation_reason||'')}</div></article>`)).join('');
  }catch(e){}
}

async function openProduct(id){
  try{
    const p=await api('/api/products/'+id);
    const inCart=state.cart.find(c=>c.product_id===id);
    $('#productDetail').innerHTML=`<div class="detail-grid">
      <img src="${esc(p.image)}" alt="${esc(p.title)}" onerror="this.style.display='none'">
      <div>
        <h2 style="margin-top:0">${esc(p.title)}</h2>
        <div class="card-meta">${esc(p.category)} · ${esc(p.supplier_company)} · ${esc(p.origin)}</div>
        <div class="detail-price">${money(p.price)} <span class="card-meta">${esc(p.currency)}</span></div>
        <p>${esc(p.description)}</p>
        <div class="kv">
          <span>${t('moq')}</span><span>${p.moq}</span>
          <span>${t('stock')}</span><span>${Number(p.stock).toLocaleString()}</span>
          <span>${t('leadPh')}</span><span>${esc(p.lead_time||'')}</span>
        </div>
        <div class="qty-row">
          <label>${t('qty')}: <input id="qtyInput" type="number" min="${p.moq}" max="${p.stock}" value="${inCart?inCart.quantity:p.moq}"></label>
        </div>
        <div class="card-actions">
          <button class="primary-btn" onclick="addToCart(${p.id},${p.moq})">${t('addCart')}</button>
          <button class="ghost-btn fav-btn ${state.favIds.has(p.id)?'active':''}" onclick="toggleFav(${p.id},this)">${state.favIds.has(p.id)?'★':'☆'}</button>
        </div>
      </div>
    </div>
    <section class="similar-box"><h3>You may also like</h3><div id="similarList" class="similar-list"><span class="card-meta">Loading…</span></div>
    <p class="card-meta similar-note">Hybrid ML model: text similarity (TF-IDF) + buyers who bought together (item-based collaborative filtering and SVD). Trained mostly on synthetic demo data.</p></section>`;
    openModal('productModal');
    loadSimilar(id);
  }catch(err){toast(err.message,true);}
}
async function loadSimilar(id){
  try{
    const r=await api('/api/products/'+id+'/similar?k=6');
    $('#similarList').innerHTML=r.items.map(i=>`<button class="similar-card" onclick="openProduct(${i.id})">
      <img src="${esc(i.image)}" alt="${esc(i.title)}" loading="lazy">
      <strong>${esc(i.title)}</strong>
      <span class="card-meta">${esc(i.category)}</span>
      <span class="reason">${i.reason.bought_together}% bought together · ${i.reason.similar_text}% similar text</span>
    </button>`).join('');
  }catch(e){const b=$('#similarList');if(b)b.textContent='';}
}
window.openProduct=openProduct;

async function toggleFav(id,btn){
  if(!state.user){toast(t('needAuth'),true);openModal('authModal');return;}
  try{
    const d=await api('/api/favorites/'+id,{method:'POST'});
    if(d.saved){state.favIds.add(id);btn.classList.add('active');btn.textContent='★';}
    else{state.favIds.delete(id);btn.classList.remove('active');btn.textContent='☆';}
    renderCartCount();
  }catch(err){toast(err.message,true);}
}
window.toggleFav=toggleFav;

/* ---------- cart & orders ---------- */
function saveCart(){localStorage.setItem('sb_cart',JSON.stringify(state.cart));renderCartCount();}
function renderCartCount(){$('#cartCount').textContent=state.cart.reduce((a,c)=>a+1,0);}
async function addToCart(id,moq){
  if(!state.user){toast(t('needAuth'),true);openModal('authModal');return;}
  if(state.user.role!=='buyer'){toast(t('needBuyer'),true);return;}
  const qty=Math.max(moq,parseInt($('#qtyInput')?.value||moq));
  const line=state.cart.find(c=>c.product_id===id);
  if(line)line.quantity=qty;else{
    const p=await api('/api/products/'+id);
    state.cart.push({product_id:id,quantity:qty,title:p.title,price:p.price,moq:p.moq,stock:p.stock,image:p.image});
  }
  api('/api/interactions',{method:'POST',body:{product_id:id,event_type:'cart'}}).catch(()=>{});
  saveCart();toast(t('addCart')+' ✓');
}
window.addToCart=addToCart;

$('#cartBtn').onclick=()=>{renderCart();openModal('cartModal');};
function renderCart(){
  const box=$('#cartItems'),foot=$('#cartFooter');
  if(!state.cart.length){box.innerHTML=`<p class="empty">${t('cartEmpty')}</p>`;foot.innerHTML='';return;}
  box.innerHTML=state.cart.map((c,i)=>`<div class="cart-line">
    <span>${esc(c.title)}<br><span class="card-meta">${money(c.price)} · ${t('moq')} ${c.moq}</span></span>
    <span><input type="number" min="${c.moq}" max="${c.stock}" value="${c.quantity}" onchange="updQty(${i},this.value)">
    <button class="mini-btn danger" onclick="delLine(${i})">×</button></span>
  </div>`).join('');
  const total=state.cart.reduce((a,c)=>a+c.price*c.quantity,0);
  foot.innerHTML=`<div class="cart-total"><span>${t('total')}</span><span>${money(total)}</span></div>
    <button class="primary-btn" style="width:100%" onclick="checkout()">${t('checkout')}</button>
    <p class="hint" style="margin-top:8px">${t('orderOk').split('.')[1]?'Demo order only. No payment is collected.':''}</p>`;
}
window.updQty=(i,v)=>{state.cart[i].quantity=Math.max(state.cart[i].moq,parseInt(v)||state.cart[i].moq);saveCart();renderCart();};
window.delLine=i=>{state.cart.splice(i,1);saveCart();renderCart();};
window.checkout=async()=>{
  if(!state.user){toast(t('needAuth'),true);closeModal('cartModal');openModal('authModal');return;}
  try{
    const d=await api('/api/orders',{method:'POST',body:{items:state.cart.map(c=>({product_id:c.product_id,quantity:c.quantity}))}});
    state.cart=[];saveCart();closeModal('cartModal');toast(t('orderOk'));
  }catch(err){toast(err.message,true);}
};

/* ---------- suppliers ---------- */
async function renderSuppliers(){
  const q=$('#sSearch').value.trim();
  const rows=await api('/api/suppliers'+(q?'?q='+encodeURIComponent(q):''));
  $('#supplierGrid').innerHTML=rows.map(s=>`<div class="row-item">
    <div class="row-head"><b>${esc(s.company)}</b><span class="chip">${esc(s.country||'')}</span></div>
    <p class="muted">${esc(s.name)} · ${s.product_count} ${t('products')}</p>
  </div>`).join('')||`<p class="empty">${t('productsEmpty')}</p>`;
}
$('#sSearch').addEventListener('input',()=>{clearTimeout(deb);deb=setTimeout(renderSuppliers,350);});

/* ---------- RFQs ---------- */
async function renderRfqs(){
  const u=state.user;
  $('#rfqAnon').classList.toggle('hidden',!!u);
  $('#rfqBuyer').classList.toggle('hidden',!(u&&u.role==='buyer'));
  $('#rfqSupplier').classList.toggle('hidden',!(u&&u.role==='supplier'));
  if(!u)return;
  const rows=await api('/api/rfqs');
  if(u.role==='buyer'){
    $('#myRfqs').innerHTML=rows.map(r=>`<div class="row-item">
      <div class="row-head"><b>${esc(r.title)}</b><span class="badge open">${esc(r.status)}</span></div>
      <p class="muted">${t('qty')}: ${r.quantity}${r.target_price?' · '+t('rfqTargetPh')+': '+money(r.target_price):''}${r.destination?' · '+esc(r.destination):''}</p>
      <p>${esc(r.details||'')}</p>
      <button class="mini-btn" onclick="openQuotes(${r.id},'${esc(r.title).replace(/'/g,"\\'")}')">${t('viewQuotes')}</button>
    </div>`).join('')||`<p class="empty">${t('rfqsEmpty')}</p>`;
  }else{
    $('#openRfqs').innerHTML=rows.map(r=>`<div class="row-item">
      <div class="row-head"><b>${esc(r.title)}</b><span class="muted">${esc(r.buyer_company||'')} · ${r.quote_count??0} ${t('quotesFor').toLowerCase()}</span></div>
      <p class="muted">${t('qty')}: ${r.quantity}${r.target_price?' · '+money(r.target_price):''}${r.destination?' · '+esc(r.destination):''}</p>
      <p>${esc(r.details||'')}</p>
      <form class="qty-row" onsubmit="return submitQuote(event,${r.id})">
        <input required type="number" min="0.01" step="0.01" id="qPrice${r.id}" placeholder="${t('pricePh')}">
        <input id="qLead${r.id}" placeholder="${t('leadPh')}">
        <input id="qNotes${r.id}" placeholder="${t('notesPh')}">
        <button class="mini-btn" type="submit">${t('submitQuote')}</button>
      </form>
    </div>`).join('')||`<p class="empty">${t('rfqsEmpty')}</p>`;
  }
}
$('#rfqForm').onsubmit=async e=>{
  e.preventDefault();
  try{
    await api('/api/rfqs',{method:'POST',body:{title:$('#rqTitle').value,details:$('#rqDetails').value,quantity:parseInt($('#rqQty').value)||1,target_price:$('#rqTarget').value?parseFloat($('#rqTarget').value):null,destination:$('#rqDest').value}});
    e.target.reset();toast(t('rfqOk'));renderRfqs();
  }catch(err){toast(err.message,true);}
};
window.submitQuote=async(e,id)=>{
  e.preventDefault();
  try{
    await api(`/api/rfqs/${id}/quotes`,{method:'POST',body:{price:parseFloat($('#qPrice'+id).value),lead_time:$('#qLead'+id).value||'7-15 days',notes:$('#qNotes'+id).value}});
    toast(t('quoteOk'));renderRfqs();
  }catch(err){toast(err.message,true);}
  return false;
};
window.openQuotes=async(id,title)=>{
  try{
    const rows=await api(`/api/rfqs/${id}/quotes`);
    $('#quotesBody').innerHTML=`<h2 style="margin-top:0">${t('quotesFor')} “${esc(title)}”</h2>`+
      (rows.length?rows.map((q,i)=>`<div class="row-item ${i===0?'quote-best':''}">
        <div class="row-head"><b>${money(q.price)} ${esc(q.currency)}</b>${i===0?`<span class="badge">${t('best')}</span>`:''}</div>
        <p class="muted">${esc(q.supplier_company)} · ${esc(q.supplier_country||'')} · ${esc(q.lead_time||'')}</p>
        ${q.notes?`<p>${esc(q.notes)}</p>`:''}
      </div>`).join(''):`<p class="empty">${t('noQuotes')}</p>`);
    openModal('quotesModal');
  }catch(err){toast(err.message,true);}
};

/* ---------- dashboard ---------- */
async function renderDashboard(){
  const u=state.user;
  $('#dashAnon').classList.toggle('hidden',!!u);
  if(!u){$('#dashStats').innerHTML='';$('#dashOrders').innerHTML='';$('#dashFavs').innerHTML='';$('#supplierAdmin').classList.add('hidden');return;}
  const d=await api('/api/dashboard');
  $('#dashStats').innerHTML=Object.entries(d.stats).map(([k,v])=>`<div class="stat"><b>${v}</b><span>${esc(k)}</span></div>`).join('');
  const orders=await api('/api/orders');
  $('#dashOrders').innerHTML=orders.map(o=>`<div class="row-item">
    <div class="row-head"><b>#${o.id} · ${money(o.total)}</b><span class="badge ${esc(o.status)}">${esc(o.status)}</span></div>
    <p class="muted">${o.items.map(i=>esc(i.title)+' ×'+i.quantity).join(' · ')}</p>
  </div>`).join('')||`<p class="empty">${t('ordersEmpty')}</p>`;
  if(u.role==='buyer'){
    $('#supplierAdmin').classList.add('hidden');
    const favs=await api('/api/favorites');
    $('#dashFavs').innerHTML=favs.map(p=>`<div class="row-item"><div class="row-head"><b>${esc(p.title)}</b><span class="card-price">${money(p.price)}</span></div><p class="muted">${esc(p.supplier_company)} · ${esc(p.origin)}</p></div>`).join('')||`<p class="empty">${t('favsEmpty')}</p>`;
  }else{
    $('#supplierAdmin').classList.remove('hidden');
    $('#dashFavs').innerHTML='';
    renderMyProducts();
  }
}
async function renderMyProducts(){
  const rows=await api('/api/supplier/products');
  $('#myProducts').innerHTML=rows.map(p=>`<div class="row-item">
    <div class="row-head"><b>${esc(p.title)}</b><span class="card-price">${money(p.price)}</span></div>
    <p class="muted">${esc(p.category)} · ${t('stock')}: ${p.stock} · ${t('moq')}: ${p.moq}</p>
    <button class="mini-btn" onclick='editProduct(${JSON.stringify(p).replace(/'/g,"&#39;")})'>${t('edit')}</button>
    <button class="mini-btn danger" onclick="deleteProduct(${p.id})">${t('remove')}</button>
  </div>`).join('')||`<p class="empty">${t('productsEmpty')}</p>`;
}
window.editProduct=p=>{
  $('#pId').value=p.id;$('#pTitle').value=p.title;$('#pCategory').value=p.category;$('#pPrice').value=p.price;
  $('#pMoq').value=p.moq;$('#pStock').value=p.stock;$('#pOrigin').value=p.origin;$('#pLead').value=p.lead_time;
  $('#pTags').value=p.tags||'';$('#pImage').value=p.image||'';$('#pDesc').value=p.description||'';
  $('#pCancel').classList.remove('hidden');$('#pTitle').focus();
};
$('#pCancel').onclick=()=>{$('#productForm').reset();$('#pId').value='';$('#pCancel').classList.add('hidden');};
$('#productForm').onsubmit=async e=>{
  e.preventDefault();
  const body={title:$('#pTitle').value,category:$('#pCategory').value,description:$('#pDesc').value,price:parseFloat($('#pPrice').value),
    moq:parseInt($('#pMoq').value)||1,stock:parseInt($('#pStock').value)||0,origin:$('#pOrigin').value,lead_time:$('#pLead').value||'7-15 days',
    tags:$('#pTags').value,image:$('#pImage').value};
  try{
    const id=$('#pId').value;
    if(id)await api('/api/products/'+id,{method:'PUT',body});
    else await api('/api/products',{method:'POST',body});
    e.target.reset();$('#pId').value='';$('#pCancel').classList.add('hidden');
    toast(t('pSave')+' ✓');renderMyProducts();loadProducts();
  }catch(err){toast(err.message,true);}
};
window.deleteProduct=async id=>{
  try{await api('/api/products/'+id,{method:'DELETE'});renderMyProducts();loadProducts();}
  catch(err){toast(err.message,true);}
};

/* ---------- modals ---------- */
function openModal(id){$('#'+id).classList.remove('hidden');}
function closeModal(id){$('#'+id).classList.add('hidden');}
$$('[data-close]').forEach(b=>b.onclick=()=>closeModal(b.dataset.close));
$$('.modal-backdrop').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.add('hidden');}));

$('#langToggle').onclick=()=>{state.lang=state.lang==='ar'?'en':'ar';localStorage.setItem('sb_lang',state.lang);applyLang();};

function renderAll(){renderAuth();renderProducts();renderCartCount();if(!$('#view-suppliers').classList.contains('hidden'))renderSuppliers();if(!$('#view-rfqs').classList.contains('hidden'))renderRfqs();if(!$('#view-dashboard').classList.contains('hidden'))renderDashboard();}

/* ---------- boot ---------- */
(async()=>{
  applyLang();
  renderCartCount();
  try{const d=await api('/api/me');state.user=d.user;}catch(e){}
  renderAuth();
  await loadProducts();
  await loadFilters();
  await loadRecos();
  if(state.user&&state.user.role==='buyer'){try{const favs=await api('/api/favorites');state.favIds=new Set(favs.map(f=>f.id));renderProducts();}catch(e){}}
  renderSuppliers();
})();
