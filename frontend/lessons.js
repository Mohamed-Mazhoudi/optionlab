// Contenu pédagogique d'OptionLab : leçons + quiz.
// Chaque leçon : id, module, title, level, minutes, body (HTML), try (bouton vers le labo), quiz.
// Les exemples chiffrés utilisent S = 100, K = 100, T = 1 an, r = 5 %, σ = 20 % sauf mention contraire.
const LESSONS = [
  // ===================== MODULE 1 =====================
  {
    id: "option", module: "1. Les bases", title: "Qu'est-ce qu'une option ?", level: "Débutant", minutes: 6,
    body: `
      <p>Une <b>option</b> est un contrat qui donne à son acheteur le <b>droit, mais pas l'obligation</b>, d'acheter ou de vendre un actif
      (le <i>sous-jacent</i> : une action, un indice, une devise…) à un prix fixé à l'avance, le <b>strike</b> K, jusqu'à ou à une date donnée, l'<b>échéance</b> T.</p>
      <ul>
        <li>Un <b>call</b> donne le droit d'<b>acheter</b> au prix K. On en achète quand on anticipe une hausse.</li>
        <li>Un <b>put</b> donne le droit de <b>vendre</b> au prix K. On en achète quand on anticipe une baisse, ou pour s'assurer.</li>
      </ul>
      <p>Ce droit a un prix : la <b>prime</b>, payée par l'acheteur au vendeur dès le départ. Le vendeur, lui, a une <b>obligation</b> : si l'acheteur exerce, il doit livrer (call) ou acheter (put).</p>
      <h3>Le payoff à l'échéance</h3>
      <div class="formula">Call : max(S<sub>T</sub> − K, 0) &nbsp;&nbsp;|&nbsp;&nbsp; Put : max(K − S<sub>T</sub>, 0)</div>
      <div class="example"><b>Exemple.</b> Tu achètes un call de strike 100 pour une prime de 10,45. À l'échéance, l'action vaut 125 :
      tu exerces, tu achètes à 100 ce qui vaut 125, soit un gain de 25 − 10,45 = <b>14,55</b>. Si l'action finit à 90, tu n'exerces pas et tu perds seulement la prime, 10,45.</div>
      <h3>Européenne ou américaine ?</h3>
      <p>Une option <b>européenne</b> ne s'exerce qu'à l'échéance ; une <b>américaine</b> à tout moment avant. Le modèle de Black-Scholes price les européennes ;
      l'arbre binomial du Pricer sait aussi pricer les américaines.</p>
      <div class="key"><b>À retenir.</b> Acheteur d'option : perte limitée à la prime. Vendeur : il encaisse la prime mais son risque peut être très grand (illimité pour un call vendu « à découvert »).</div>`,
    try: { label: "Voir le payoff d'un achat de call →", tab: "strategy", preset: "long_call" },
    quiz: [
      { q: "Un put donne à son acheteur…", choices: ["l'obligation de vendre au strike", "le droit de vendre au strike", "le droit d'acheter au strike", "l'obligation d'acheter au strike"], answer: 1,
        explain: "Put = droit de vendre. L'obligation est du côté du vendeur du put, qui doit acheter si l'acheteur exerce." },
      { q: "Tu achètes un call K = 50 pour 3 €. À l'échéance S = 51. Ton gain net ?", choices: ["+1 €", "−2 €", "−3 €", "+4 €"], answer: 1,
        explain: "Payoff = max(51 − 50, 0) = 1, moins la prime de 3 : −2 €. Exercer reste utile car ça réduit la perte." },
      { q: "Quelle position a une perte potentiellement illimitée ?", choices: ["Achat de call", "Achat de put", "Vente de call", "Vente de put"], answer: 2,
        explain: "Si tu vends un call et que l'action monte sans limite, tu dois livrer une action dont le prix n'a pas de plafond. (La vente de put a une perte max de K − prime.)" },
    ],
  },
  {
    id: "valeur-temps", module: "1. Les bases", title: "Valeur intrinsèque et valeur temps", level: "Débutant", minutes: 5,
    body: `
      <p>Avant l'échéance, le prix d'une option se décompose en deux parties :</p>
      <div class="formula">Prime = valeur intrinsèque + valeur temps</div>
      <ul>
        <li><b>Valeur intrinsèque</b> : ce que rapporterait l'exercice immédiat, soit max(S − K, 0) pour un call.</li>
        <li><b>Valeur temps</b> : le reste. Elle paie la <i>possibilité</i> que l'option gagne encore de la valeur d'ici l'échéance. Elle fond à mesure que l'échéance approche.</li>
      </ul>
      <h3>Dans, à ou hors de la monnaie</h3>
      <table>
        <tr><th></th><th>Call</th><th>Put</th></tr>
        <tr><td>Dans la monnaie (ITM)</td><td>S &gt; K</td><td>S &lt; K</td></tr>
        <tr><td>À la monnaie (ATM)</td><td>S ≈ K</td><td>S ≈ K</td></tr>
        <tr><td>Hors de la monnaie (OTM)</td><td>S &lt; K</td><td>S &gt; K</td></tr>
      </table>
      <div class="example"><b>Exemple</b> (S = 100, 1 an, σ = 20 %). Call K = 90 : prime 16,70 = 10 de valeur intrinsèque + 6,70 de valeur temps.
      Call K = 110 : prime 6,04, entièrement de la valeur temps. Call K = 100 : prime 10,45, entièrement de la valeur temps aussi.</div>
      <div class="key"><b>À retenir.</b> La valeur temps est maximale à la monnaie : c'est là que l'incertitude sur l'exercice est la plus forte.</div>`,
    try: { label: "Observer le prix d'un call selon le spot →", tab: "pricer", curve: "price", option: "call" },
    quiz: [
      { q: "Un call K = 80 vaut 23 quand S = 100. Sa valeur temps ?", choices: ["23", "20", "3", "0"], answer: 2,
        explain: "Valeur intrinsèque = 100 − 80 = 20, donc valeur temps = 23 − 20 = 3." },
      { q: "Un put K = 100 quand S = 120 est…", choices: ["dans la monnaie", "à la monnaie", "hors de la monnaie"], answer: 2,
        explain: "Un put rapporte quand S < K. Ici S > K : il est hors de la monnaie, sa prime n'est que de la valeur temps." },
      { q: "À l'échéance, la valeur temps d'une option est…", choices: ["maximale", "nulle", "égale à la prime initiale"], answer: 1,
        explain: "À l'échéance il n'y a plus d'incertitude : l'option vaut exactement sa valeur intrinsèque." },
    ],
  },
  {
    id: "parite", module: "1. Les bases", title: "La parité call-put", level: "Intermédiaire", minutes: 6,
    body: `
      <p>Pour des options européennes de même strike et même échéance, sans arbitrage :</p>
      <div class="formula">C − P = S − K·e<sup>−rT</sup> &nbsp;&nbsp;(avec dividende : C − P = S·e<sup>−qT</sup> − K·e<sup>−rT</sup>)</div>
      <h3>Pourquoi ?</h3>
      <p>Compare deux portefeuilles : (A) un call acheté + K·e<sup>−rT</sup> placés au taux sans risque ; (B) un put acheté + une action.
      À l'échéance, les deux valent <b>max(S<sub>T</sub>, K)</b>, quel que soit S<sub>T</sub>. Deux portefeuilles qui valent la même chose demain doivent coûter la même chose aujourd'hui, sinon on pourrait gagner sans risque (un <b>arbitrage</b>).</p>
      <div class="example"><b>Vérification.</b> Call = 10,45, put = 5,57. C − P = 4,88. Et S − K·e<sup>−0,05</sup> = 100 − 95,12 = 4,88. ✓</div>
      <div class="key"><b>À retenir.</b> Connaissant le prix du call, on connaît celui du put (et inversement). Les tests du projet vérifient cette égalité à 10<sup>−9</sup> près.</div>`,
    try: { label: "Comparer call et put dans le Pricer →", tab: "pricer", curve: "price", option: "put" },
    quiz: [
      { q: "S = 100, K = 100, r = 0. Le call vaut 8. Le put vaut…", choices: ["8", "0", "16", "Impossible à savoir"], answer: 0,
        explain: "Avec r = 0 : C − P = S − K = 0, donc P = C = 8." },
      { q: "Call acheté + put vendu (même K, même T) reproduit…", choices: ["une obligation", "un contrat à terme (achat de l'action à K)", "un straddle"], answer: 1,
        explain: "À l'échéance on paie K et on reçoit l'action dans tous les cas : c'est un achat à terme au prix K." },
      { q: "Si le marché viole la parité, on peut…", choices: ["réaliser un arbitrage", "rien faire", "seulement perdre"], answer: 0,
        explain: "On achète le portefeuille trop bon marché et on vend l'autre : gain certain sans risque." },
    ],
  },
  // ===================== MODULE 2 =====================
  {
    id: "black-scholes", module: "2. Pricing", title: "Le modèle de Black-Scholes", level: "Intermédiaire", minutes: 9,
    body: `
      <p>En 1973, Fischer Black, Myron Scholes et Robert Merton donnent une formule fermée pour le prix d'une option européenne. Hypothèses principales :</p>
      <ul>
        <li>le cours suit un <b>mouvement brownien géométrique</b> (rendements log-normaux) de volatilité σ constante ;</li>
        <li>taux sans risque r constant, pas de frais de transaction, on peut acheter et vendre en continu ;</li>
        <li>pas d'opportunité d'arbitrage.</li>
      </ul>
      <div class="formula">C = S·N(d<sub>1</sub>) − K·e<sup>−rT</sup>·N(d<sub>2</sub>) &nbsp;&nbsp;&nbsp; P = K·e<sup>−rT</sup>·N(−d<sub>2</sub>) − S·N(−d<sub>1</sub>)</div>
      <div class="formula">d<sub>1</sub> = [ln(S/K) + (r + σ²/2)·T] / (σ√T) &nbsp;&nbsp;&nbsp; d<sub>2</sub> = d<sub>1</sub> − σ√T</div>
      <p>N est la fonction de répartition de la loi normale centrée réduite.</p>
      <h3>L'intuition</h3>
      <p>On peut répliquer l'option avec un portefeuille d'actions et de cash réajusté en continu (c'est le delta hedging, module 5). Comme ce portefeuille élimine le risque,
      il doit rapporter r : le prix ne dépend donc <b>pas</b> du rendement espéré de l'action, seulement de σ. C'est le <b>pricing risque-neutre</b>.</p>
      <ul>
        <li>N(d<sub>2</sub>) = probabilité (risque-neutre) que le call finisse dans la monnaie.</li>
        <li>N(d<sub>1</sub>) = delta du call.</li>
      </ul>
      <div class="example"><b>Exemple.</b> S = K = 100, T = 1, r = 5 %, σ = 20 % : d<sub>1</sub> = 0,35, d<sub>2</sub> = 0,15, N(d<sub>1</sub>) = 0,637, N(d<sub>2</sub>) = 0,560. Call = 100 × 0,637 − 95,12 × 0,560 = <b>10,45</b>.</div>
      <div class="key"><b>À retenir.</b> 5 entrées : S, K, T, r, σ. Une seule n'est pas observable directement : la volatilité.</div>`,
    try: { label: "Ouvrir le Pricer (S = 100, σ = 20 %, T = 1) →", tab: "pricer", S: 100, sigma: 0.2, T: 1, r: 0.05, K: 100, curve: "price", option: "call" },
    quiz: [
      { q: "Dans Black-Scholes, le prix d'un call dépend-il du rendement espéré de l'action ?", choices: ["Oui, beaucoup", "Non", "Seulement pour les puts"], answer: 1,
        explain: "Grâce à la réplication, seul σ compte (avec S, K, T, r). C'est le résultat clé du pricing risque-neutre." },
      { q: "Si la volatilité passe de 20 % à 30 % (ATM, 1 an), le call…", choices: ["baisse", "ne bouge pas", "monte (≈ 10,45 → 14,23)"], answer: 2,
        explain: "Plus de volatilité = plus de chances de finir loin dans la monnaie, alors que la perte reste limitée à la prime. Call et put montent tous les deux." },
      { q: "N(d₂) s'interprète comme…", choices: ["le delta du put", "la probabilité risque-neutre d'exercice du call", "le gamma"], answer: 1,
        explain: "N(d₂) = probabilité, sous la mesure risque-neutre, que S_T > K." },
    ],
  },
  {
    id: "numerique", module: "2. Pricing", title: "Arbre binomial et Monte-Carlo", level: "Intermédiaire", minutes: 7,
    body: `
      <p>Black-Scholes n'a de formule fermée que pour les cas simples. Pour le reste, on utilise des méthodes numériques. Le Pricer en affiche deux.</p>
      <h3>L'arbre binomial (Cox-Ross-Rubinstein)</h3>
      <p>On découpe le temps en N pas. À chaque pas, le cours monte (×u) ou baisse (×d), avec u = e<sup>σ√Δt</sup> et d = 1/u.
      On part des payoffs à l'échéance et on remonte l'arbre en actualisant l'espérance risque-neutre :</p>
      <div class="formula">V = e<sup>−rΔt</sup> · [ p·V<sub>haut</sub> + (1 − p)·V<sub>bas</sub> ] &nbsp;&nbsp; avec p = (e<sup>(r−q)Δt</sup> − d) / (u − d)</div>
      <p>Avantage : pour une option <b>américaine</b>, on compare à chaque nœud avec la valeur d'exercice immédiat et on garde le maximum.
      Quand N augmente, le prix converge vers Black-Scholes.</p>
      <h3>Monte-Carlo</h3>
      <p>On simule des milliers de cours finaux S<sub>T</sub> possibles, on calcule le payoff de chacun, on fait la moyenne et on actualise.
      L'erreur diminue en 1/√(nombre de simulations) : il faut 4 fois plus de tirages pour diviser l'erreur par 2. On utilise des <b>variables antithétiques</b> (z et −z) pour réduire la variance.</p>
      <div class="key"><b>À retenir.</b> Le binomial excelle pour les américaines ; Monte-Carlo pour les produits complexes (plusieurs sous-jacents, payoffs dépendant du chemin).</div>`,
    try: { label: "Comparer les 3 méthodes dans le Pricer →", tab: "pricer", option: "put", curve: "price" },
    quiz: [
      { q: "Pourquoi un put américain vaut-il plus qu'un put européen ?", choices: ["Il a un strike plus élevé", "On peut l'exercer tôt, ce qui peut être optimal", "À cause des dividendes uniquement"], answer: 1,
        explain: "Quand le put est très dans la monnaie, toucher K tout de suite (et placer l'argent au taux r) peut valoir mieux qu'attendre." },
      { q: "Pour diviser par 2 l'erreur d'un Monte-Carlo, il faut…", choices: ["2 fois plus de tirages", "4 fois plus de tirages", "10 fois plus de tirages"], answer: 1,
        explain: "Erreur ∝ 1/√n : pour la diviser par 2, il faut multiplier n par 4." },
      { q: "Sans dividende, un call américain vaut…", choices: ["plus que l'européen", "autant que l'européen", "moins que l'européen"], answer: 1,
        explain: "Exercer un call tôt sans dividende n'est jamais optimal (on perd la valeur temps et les intérêts sur K). Le test du projet le vérifie." },
    ],
  },
  {
    id: "vol-implicite", module: "2. Pricing", title: "La volatilité implicite", level: "Intermédiaire", minutes: 6,
    body: `
      <p>Sur le marché, on <b>observe</b> le prix des options. On peut alors inverser Black-Scholes : quelle volatilité σ redonne ce prix ? C'est la <b>volatilité implicite</b>.</p>
      <h3>Comment la calculer ?</h3>
      <p>Il n'y a pas de formule fermée. On utilise <b>Newton-Raphson</b> : on part d'un σ initial et on corrige avec la dérivée du prix par rapport à σ, qui est le vega :</p>
      <div class="formula">σ<sub>n+1</sub> = σ<sub>n</sub> − [ BS(σ<sub>n</sub>) − prix observé ] / vega(σ<sub>n</sub>)</div>
      <p>Si Newton diverge (vega trop petit, option très hors de la monnaie), le code se replie sur une <b>dichotomie</b>, plus lente mais toujours convergente car le prix croît avec σ.</p>
      <h3>Historique ou implicite ?</h3>
      <ul>
        <li><b>Historique</b> (ou réalisée) : calculée sur les cours passés (onglet Marché, bouton Charger).</li>
        <li><b>Implicite</b> : ce que le marché anticipe pour le futur, déduit des prix d'options. L'indice <b>VIX</b> mesure la vol implicite du S&amp;P 500.</li>
      </ul>
      <p>En pratique, la vol implicite varie selon le strike : c'est le <b>smile</b> (ou le <i>skew</i> sur les actions, où les puts hors de la monnaie sont plus chers). C'est une preuve que l'hypothèse de σ constant est fausse.</p>
      <div class="key"><b>À retenir.</b> Les traders cotent les options en vol implicite plutôt qu'en prix : « ce call se traite à 22 de vol ».</div>`,
    try: { label: "Calculer une vol implicite →", tab: "iv" },
    quiz: [
      { q: "La vol implicite est…", choices: ["calculée sur les cours passés", "déduite du prix de marché d'une option", "toujours égale à 20 %"], answer: 1,
        explain: "On inverse Black-Scholes à partir du prix observé." },
      { q: "Pourquoi Newton-Raphson utilise-t-il le vega ?", choices: ["C'est la dérivée du prix par rapport à σ", "C'est la dérivée par rapport au spot", "Par convention"], answer: 0,
        explain: "Newton a besoin de f'(σ) ; ici f'(σ) = ∂Prix/∂σ = vega." },
      { q: "Le « smile » de volatilité montre que…", choices: ["Black-Scholes est parfait", "la vol implicite dépend du strike", "les options sont gratuites"], answer: 1,
        explain: "Si le modèle était exact, toutes les options auraient la même vol implicite. Le smile révèle les queues épaisses et la peur des krachs." },
    ],
  },
  // ===================== MODULE 3 =====================
  {
    id: "delta", module: "3. Les greeks", title: "Le delta", level: "Intermédiaire", minutes: 6,
    body: `
      <p>Les <b>greeks</b> mesurent la sensibilité du prix d'une option à chaque paramètre. Le premier et le plus important est le <b>delta</b> :</p>
      <div class="formula">Δ = ∂Prix / ∂S &nbsp;&nbsp;&nbsp; Call : Δ = N(d<sub>1</sub>) ∈ [0 ; 1] &nbsp;&nbsp; Put : Δ = N(d<sub>1</sub>) − 1 ∈ [−1 ; 0]</div>
      <p>Il répond à la question : <b>si l'action monte de 1 €, de combien bouge l'option ?</b></p>
      <div class="example"><b>Exemple.</b> Call ATM 1 an : Δ = 0,637. Si S passe de 100 à 101, le call passe de 10,45 à environ 11,10 (+0,65 ≈ Δ).</div>
      <h3>Trois façons de lire le delta</h3>
      <ul>
        <li><b>Sensibilité</b> : variation du prix pour 1 € de sous-jacent.</li>
        <li><b>Équivalent action</b> : 100 calls de delta 0,6 se comportent (localement) comme 60 actions.</li>
        <li><b>Ratio de couverture</b> : pour neutraliser un call vendu, on achète Δ actions (module 5).</li>
      </ul>
      <p>Un call très dans la monnaie a un delta proche de 1 (il bouge comme l'action), un call très hors de la monnaie un delta proche de 0.</p>
      <div class="key"><b>À retenir.</b> Δ<sub>call</sub> − Δ<sub>put</sub> = 1 (sans dividende), conséquence directe de la parité call-put.</div>`,
    try: { label: "Tracer le delta selon le spot →", tab: "pricer", curve: "delta", option: "call" },
    quiz: [
      { q: "Un call a un delta de 0,4. L'action gagne 2 €. Le call gagne environ…", choices: ["0,4 €", "0,8 €", "2 €"], answer: 1,
        explain: "ΔPrix ≈ Δ × ΔS = 0,4 × 2 = 0,8 €." },
      { q: "Le delta d'un put est…", choices: ["entre 0 et 1", "entre −1 et 0", "toujours −0,5"], answer: 1,
        explain: "Le put perd de la valeur quand l'action monte : son delta est négatif." },
      { q: "Tu as vendu 100 calls de delta 0,55. Pour être neutre en delta, tu…", choices: ["vends 55 actions", "achètes 55 actions", "achètes 100 actions"], answer: 1,
        explain: "100 calls vendus = −55 en delta. Il faut +55 : acheter 55 actions." },
    ],
  },
  {
    id: "gamma", module: "3. Les greeks", title: "Le gamma", level: "Intermédiaire", minutes: 6,
    body: `
      <p>Le delta change quand le cours bouge. Le <b>gamma</b> mesure cette variation :</p>
      <div class="formula">Γ = ∂Δ / ∂S = ∂²Prix / ∂S² = N'(d<sub>1</sub>) / (S·σ·√T)</div>
      <p>Il est <b>identique pour un call et un put</b> de même strike, toujours positif pour un acheteur, et <b>maximal à la monnaie</b>, surtout près de l'échéance.</p>
      <div class="example"><b>Exemple.</b> Call ATM 1 an : Γ = 0,0188. Si S monte de 100 à 105, le delta passe d'environ 0,637 à 0,637 + 5 × 0,0188 ≈ 0,73.</div>
      <h3>Pourquoi c'est important</h3>
      <ul>
        <li><b>Long gamma</b> (acheteur d'options) : quand le marché bouge fort, ton delta évolue dans le bon sens. Tu aimes la volatilité.</li>
        <li><b>Short gamma</b> (vendeur d'options) : chaque grand mouvement joue contre toi et t'oblige à racheter cher ou revendre bas pour te recouvrir.</li>
      </ul>
      <div class="key"><b>À retenir.</b> Le gamma, c'est la convexité. On ne l'a pas gratuitement : il se paie avec le theta (leçon suivante).</div>`,
    try: { label: "Tracer le gamma selon le spot →", tab: "pricer", curve: "gamma" },
    quiz: [
      { q: "Où le gamma d'une option est-il le plus élevé ?", choices: ["Très dans la monnaie", "À la monnaie", "Très hors de la monnaie"], answer: 1,
        explain: "C'est autour du strike que le delta passe rapidement de ~0 à ~1." },
      { q: "Un call et un put de même strike et même échéance ont…", choices: ["le même gamma", "des gammas opposés", "aucun gamma"], answer: 0,
        explain: "Par la parité, call − put = action − cash ; la dérivée seconde de l'action est nulle, donc Γ_call = Γ_put." },
      { q: "Un vendeur de straddle est…", choices: ["long gamma", "short gamma", "neutre en gamma"], answer: 1,
        explain: "Il a vendu deux options : son gamma est négatif, il souffre des grands mouvements." },
    ],
  },
  {
    id: "vega-theta-rho", module: "3. Les greeks", title: "Vega, theta et rho", level: "Intermédiaire", minutes: 7,
    body: `
      <h3>Vega : la sensibilité à la volatilité</h3>
      <div class="formula">Vega = ∂Prix / ∂σ = S·N'(d<sub>1</sub>)·√T &nbsp;&nbsp;(affiché pour +1 point de vol)</div>
      <p>Toujours positif pour un acheteur. Call ATM 1 an : vega = 0,375, donc si la vol passe de 20 % à 21 %, le call gagne environ 0,38. Le vega est plus grand pour les options longues.</p>
      <h3>Theta : l'érosion du temps</h3>
      <p>Le <b>theta</b> mesure la perte de valeur quand un jour passe, tout le reste égal. Il est en général négatif pour un acheteur : c'est la fonte de la valeur temps.
      Call ATM 1 an : theta ≈ −0,018 par jour. Le theta s'accélère à l'approche de l'échéance pour les options à la monnaie.</p>
      <div class="key"><b>Le compromis gamma / theta.</b> Pour une position couverte en delta, sur un petit intervalle de temps :
      <div class="formula">P&amp;L ≈ ½·Γ·(ΔS)² + Θ·Δt</div>
      L'acheteur paie du theta chaque jour et gagne grâce au gamma si le marché bouge assez. Le vendeur fait l'inverse.</div>
      <h3>Rho : la sensibilité aux taux</h3>
      <p>Le <b>rho</b> mesure l'effet d'une hausse de 1 point du taux sans risque. Positif pour un call (l'actualisation de K diminue), négatif pour un put. Souvent le moins important des greeks, sauf pour les options très longues.</p>`,
    try: { label: "Tracer le theta selon le spot →", tab: "pricer", curve: "theta" },
    quiz: [
      { q: "Tu achètes un call. Toutes choses égales, un jour passe. Ton call…", choices: ["prend de la valeur", "perd un peu de valeur (theta)", "ne bouge pas"], answer: 1,
        explain: "La valeur temps fond chaque jour : c'est le theta, négatif pour l'acheteur." },
      { q: "La vol implicite monte de 2 points, ton vega vaut 0,3. Ton option gagne…", choices: ["0,3", "0,6", "2"], answer: 1,
        explain: "ΔPrix ≈ vega × Δσ (en points) = 0,3 × 2 = 0,6." },
      { q: "Le rho d'un put est en général…", choices: ["positif", "négatif", "nul"], answer: 1,
        explain: "Un taux plus élevé réduit la valeur actualisée du strike que touche le détenteur du put : le put baisse." },
    ],
  },
  // ===================== MODULE 4 =====================
  {
    id: "spreads", module: "4. Stratégies", title: "Les spreads directionnels", level: "Intermédiaire", minutes: 6,
    body: `
      <p>Un <b>spread</b> combine l'achat et la vente d'options du même type mais de strikes différents. On réduit le coût en renonçant à une partie du gain.</p>
      <h3>Bull call spread (haussier modéré)</h3>
      <p>Achat d'un call K<sub>1</sub> + vente d'un call K<sub>2</sub> &gt; K<sub>1</sub>. La prime encaissée sur le call vendu finance une partie du call acheté.</p>
      <ul>
        <li>Perte max = coût net ; gain max = (K<sub>2</sub> − K<sub>1</sub>) − coût net ; point mort = K<sub>1</sub> + coût net.</li>
      </ul>
      <div class="example"><b>Exemple</b> (S = 100, 6 mois, σ = 25 %, r = 3 %). Call 100 acheté, call 105 vendu : coût net 2,18. Gain max 5 − 2,18 = <b>2,82</b>, perte max <b>2,18</b>, point mort <b>102,18</b>.</div>
      <h3>Bear put spread (baissier modéré)</h3>
      <p>Achat d'un put K<sub>1</sub> + vente d'un put K<sub>2</sub> &lt; K<sub>1</sub>. C'est le miroir du précédent.</p>
      <div class="key"><b>À retenir.</b> Les spreads ont un risque et un gain tous deux limités. Ils servent quand on a une vue directionnelle avec une cible de prix.</div>`,
    try: { label: "Construire un bull call spread →", tab: "strategy", preset: "bull_call_spread", S: 100, sigma: 0.25, T: 0.5 },
    quiz: [
      { q: "Bull call spread 50/55 pour un coût de 2. Gain max ?", choices: ["2", "3", "5", "Illimité"], answer: 1,
        explain: "Gain max = écart des strikes − coût = 5 − 2 = 3." },
      { q: "Pourquoi vendre le call 55 au lieu d'acheter seulement le call 50 ?", choices: ["Pour augmenter le gain max", "Pour réduire le coût de la position", "Pour être baissier"], answer: 1,
        explain: "La prime encaissée réduit le coût ; en échange on plafonne le gain au-delà de 55." },
      { q: "Le bear put spread est adapté à une vue…", choices: ["fortement haussière", "modérément baissière", "de forte volatilité"], answer: 1,
        explain: "Il gagne si le cours baisse, avec un gain plafonné au strike du put vendu." },
    ],
  },
  {
    id: "volatilite", module: "4. Stratégies", title: "Jouer la volatilité : straddle et strangle", level: "Intermédiaire", minutes: 7,
    body: `
      <p>Parfois on ne sait pas dans quel sens le marché va bouger, mais on pense qu'il va <b>beaucoup</b> bouger (résultats d'entreprise, décision de banque centrale…).</p>
      <h3>Long straddle</h3>
      <p>Achat d'un call et d'un put <b>au même strike</b> (souvent à la monnaie). On gagne si le cours s'éloigne du strike de plus que le coût total, dans un sens ou dans l'autre.</p>
      <div class="example"><b>Exemple</b> (S = 100, 6 mois, σ = 25 %). Le straddle 100 coûte 14,03. Points morts : <b>85,97</b> et <b>114,03</b>. Il faut un mouvement de plus de 14 % pour gagner à l'échéance.</div>
      <h3>Long strangle</h3>
      <p>Achat d'un put K<sub>1</sub> et d'un call K<sub>2</sub> &gt; K<sub>1</sub>, tous deux hors de la monnaie. Moins cher, mais il faut un mouvement encore plus grand.</p>
      <h3>Short straddle</h3>
      <p>L'inverse : on vend les deux options et on encaisse les primes. On gagne si le marché reste calme. Le risque est <b>illimité</b> : c'est une position short gamma et short vega.</p>
      <div class="key"><b>À retenir.</b> Ces stratégies sont presque neutres en delta : on parie sur l'<b>ampleur</b> du mouvement (la volatilité réalisée) par rapport à ce que le marché a déjà intégré (la vol implicite).</div>`,
    try: { label: "Construire un long straddle →", tab: "strategy", preset: "long_straddle", S: 100, sigma: 0.25, T: 0.5 },
    quiz: [
      { q: "Un straddle 100 coûte 8. Points morts à l'échéance ?", choices: ["92 et 108", "96 et 104", "100 seulement"], answer: 0,
        explain: "On gagne si |S_T − 100| > 8, donc S_T < 92 ou S_T > 108." },
      { q: "Juste avant des résultats, la vol implicite est très haute. Après l'annonce, elle s'effondre. L'acheteur de straddle…", choices: ["gagne forcément", "peut perdre même si l'action bouge", "n'est pas concerné"], answer: 1,
        explain: "C'est l'« écrasement de vol » : la baisse du vega peut effacer le gain dû au mouvement si celui-ci est plus petit qu'anticipé." },
      { q: "Le short straddle a une perte maximale…", choices: ["égale aux primes encaissées", "illimitée", "nulle"], answer: 1,
        explain: "Le call vendu expose à une hausse illimitée." },
    ],
  },
  {
    id: "range", module: "4. Stratégies", title: "Butterfly et iron condor", level: "Avancé", minutes: 6,
    body: `
      <p>Ces stratégies parient sur un cours qui reste <b>dans une zone</b>, avec un risque limité (contrairement au short straddle).</p>
      <h3>Butterfly (papillon)</h3>
      <p>1 call K − w acheté, 2 calls K vendus, 1 call K + w acheté. Gain maximal si S<sub>T</sub> = K pile ; perte limitée au coût (faible).</p>
      <h3>Iron condor</h3>
      <p>Un bull put spread (put K − 2w acheté, put K − w vendu) + un bear call spread (call K + w vendu, call K + 2w acheté). On <b>encaisse un crédit</b>.</p>
      <ul>
        <li>Gain max = crédit encaissé, si le cours finit entre les deux strikes vendus.</li>
        <li>Perte max = w − crédit, d'un côté ou de l'autre.</li>
      </ul>
      <div class="key"><b>À retenir.</b> Ce sont des positions short vega et long theta : elles gagnent avec le temps qui passe si le marché reste calme. Les « ailes » achetées servent d'assurance contre un gros mouvement.</div>`,
    try: { label: "Construire un iron condor →", tab: "strategy", preset: "iron_condor" },
    quiz: [
      { q: "Un iron condor rapporte le plus si…", choices: ["le marché s'envole", "le cours finit entre les strikes vendus", "la vol implicite explose"], answer: 1,
        explain: "Toutes les options finissent hors de la monnaie : on garde tout le crédit." },
      { q: "Pourquoi acheter les ailes dans un iron condor ?", choices: ["Pour limiter la perte maximale", "Pour gagner plus", "Pour être long gamma"], answer: 0,
        explain: "Sans ailes, ce serait un short strangle à perte illimitée." },
      { q: "Le temps qui passe est, pour un iron condor…", choices: ["favorable (theta positif)", "défavorable", "sans effet"], answer: 0,
        explain: "Position vendeuse d'options : la valeur temps qui fond profite au vendeur." },
    ],
  },
  {
    id: "assurance", module: "4. Stratégies", title: "Covered call et put de protection", level: "Débutant", minutes: 5,
    body: `
      <p>Les options servent aussi à gérer un portefeuille d'actions existant.</p>
      <h3>Covered call</h3>
      <p>Tu détiens l'action et tu <b>vends un call</b> au-dessus du cours. Tu encaisses la prime (un revenu en plus), mais tu renonces à la hausse au-delà du strike.
      C'est une stratégie de rendement, populaire dans les fonds « buy-write ».</p>
      <h3>Put de protection</h3>
      <p>Tu détiens l'action et tu <b>achètes un put</b>. Si l'action s'effondre, tu peux la revendre au strike : ta perte est plafonnée. C'est une assurance, et la prime est le coût de l'assurance.</p>
      <div class="example"><b>Combinaison : le collar.</b> Action + put acheté + call vendu. Le call vendu finance le put : on se protège presque gratuitement, en échange d'un plafond sur les gains.</div>
      <div class="key"><b>À retenir.</b> Covered call ≈ vente de put (même profil, par la parité). Put de protection ≈ achat de call.</div>`,
    try: { label: "Voir le put de protection →", tab: "strategy", preset: "protective_put" },
    quiz: [
      { q: "Le covered call est intéressant si tu penses que l'action va…", choices: ["s'envoler", "stagner ou monter un peu", "s'effondrer"], answer: 1,
        explain: "Tu gardes la prime et l'action ; si elle s'envole, tu rates la hausse au-delà du strike." },
      { q: "Le put de protection fixe…", choices: ["un gain maximal", "une perte maximale", "un dividende"], answer: 1,
        explain: "En dessous du strike, la baisse de l'action est compensée par le put." },
      { q: "Le profil d'un covered call ressemble à celui…", choices: ["d'un put vendu", "d'un call acheté", "d'un straddle"], answer: 0,
        explain: "Action − call = put − cash (parité) : même forme de payoff qu'une vente de put." },
    ],
  },
  // ===================== MODULE 5 =====================
  {
    id: "hedging", module: "5. Couverture", title: "Le delta hedging", level: "Avancé", minutes: 8,
    body: `
      <p>Une banque qui vend une option à un client ne veut pas parier sur la direction du marché. Elle se <b>couvre</b> : elle achète Δ actions (pour un call vendu),
      ce qui annule la sensibilité de sa position au premier ordre.</p>
      <h3>Le problème : le delta bouge</h3>
      <p>Comme Γ ≠ 0, le delta change dès que le cours bouge. Il faut donc <b>rebalancer</b> régulièrement : racheter des actions quand le cours monte, en revendre quand il baisse.
      Pour un vendeur d'option (short gamma), ça revient à acheter haut et vendre bas : c'est le coût de la couverture, et il est exactement payé, en moyenne, par la prime encaissée.</p>
      <h3>Ce que montre la simulation</h3>
      <ul>
        <li>Si la vol réalisée = la vol implicite utilisée pour vendre, le P&amp;L moyen est ≈ 0 : la prime couvrait exactement le coût de la couverture.</li>
        <li>Avec un rebalancement discret, il reste un <b>risque résiduel</b> qui diminue environ en 1/√N : passer de 52 à 252 rebalancements par an divise l'écart-type par ≈ 2,2.</li>
        <li>La tendance μ de l'action n'a quasiment pas d'effet : la couverture neutralise la direction. C'est la logique de Black-Scholes.</li>
        <li>Avec des frais de transaction, rebalancer très souvent devient coûteux : il y a un compromis.</li>
      </ul>
      <div class="key"><b>À retenir.</b> Le prix Black-Scholes est le coût de réplication de l'option. Le delta hedging est la façon concrète de le « gagner ».</div>`,
    try: { label: "Lancer une couverture quotidienne →", tab: "hedge", sigma: 0.25, T: 0.5, realized: 0.25, freq: 252, K: 100, S: 100 },
    quiz: [
      { q: "Tu as vendu un call de delta 0,5. L'action monte et le delta passe à 0,6. Pour rester couvert, tu…", choices: ["vends des actions", "achètes des actions", "ne fais rien"], answer: 1,
        explain: "Il te faut maintenant 0,6 action par call : tu en rachètes 0,1, à un prix plus élevé (short gamma)." },
      { q: "Si on rebalance 4 fois plus souvent, l'écart-type du P&L est environ…", choices: ["divisé par 4", "divisé par 2", "inchangé"], answer: 1,
        explain: "Risque résiduel ∝ 1/√N : √4 = 2." },
      { q: "Dans une couverture en delta, le rendement espéré μ de l'action…", choices: ["est crucial", "n'a presque pas d'effet", "doit être nul"], answer: 1,
        explain: "La position couverte est neutre en direction : seule la volatilité réalisée compte. Teste-le avec le curseur μ." },
    ],
  },
  {
    id: "vol-trading", module: "5. Couverture", title: "Gagner ou perdre sur la volatilité", level: "Avancé", minutes: 7,
    body: `
      <p>Une option couverte en delta n'est plus un pari sur la direction : c'est un <b>pari sur la volatilité</b>. Sur chaque petit intervalle, le P&amp;L d'un acheteur couvert vaut environ :</p>
      <div class="formula">dP&amp;L ≈ ½·Γ·S²·(σ<sub>réalisée</sub>² − σ<sub>implicite</sub>²)·dt</div>
      <ul>
        <li>Si la volatilité réalisée dépasse l'implicite, l'<b>acheteur couvert gagne</b> (ses gains de gamma battent le theta payé) et le vendeur perd.</li>
        <li>Si elle est plus faible, c'est l'inverse : le vendeur encaisse plus de theta qu'il ne perd en gamma.</li>
      </ul>
      <p>En moyenne, le gain ou la perte est proche de la différence de prix entre les deux vols, soit environ <b>vega × (σ<sub>réalisée</sub> − σ<sub>implicite</sub>)</b>. La simulation affiche les deux pour comparer.</p>
      <h3>Dans la vraie vie</h3>
      <p>Historiquement, la vol implicite est le plus souvent un peu <b>au-dessus</b> de la vol réalisée : c'est la <i>prime de risque de volatilité</i>, la rémunération des vendeurs d'options pour le risque de krach.
      Mais lors d'un krach (mars 2020, par exemple), la vol réalisée explose et les vendeurs subissent de lourdes pertes.</p>
      <div class="key"><b>À retenir.</b> Pour un trader d'options, la question n'est pas « est-ce que ça va monter ? » mais « est-ce que ça va bouger plus ou moins que ce que le marché anticipe ? ».</div>`,
    try: { label: "Simuler une vol réalisée de 40 % pour une option vendue à 25 % →", tab: "hedge", S: 100, K: 100, sigma: 0.25, T: 0.5, realized: 0.4, freq: 52 },
    quiz: [
      { q: "Option vendue à 20 % de vol implicite, vol réalisée 30 %. Le vendeur couvert…", choices: ["gagne", "perd", "est à zéro"], answer: 1,
        explain: "Il est short gamma : le marché a bougé plus que ce qu'il a facturé." },
      { q: "Un acheteur couvert gagne si…", choices: ["l'action monte", "la vol réalisée dépasse la vol implicite payée", "les taux montent"], answer: 1,
        explain: "Couvert en delta, il ne dépend plus de la direction mais de l'ampleur des mouvements." },
      { q: "La « prime de risque de volatilité » signifie qu'en moyenne…", choices: ["la vol implicite est au-dessus de la réalisée", "la vol réalisée est au-dessus de l'implicite", "les deux sont toujours égales"], answer: 0,
        explain: "Les acheteurs paient une assurance ; les vendeurs sont rémunérés pour porter le risque de krach." },
    ],
  },
];
