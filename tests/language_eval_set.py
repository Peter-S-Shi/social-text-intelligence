# ruff: noqa: E501  (sentences are data, not code)
"""A small synthetic evaluation set for the language detector.

Every text is invented for this project (no real posts, people, or accounts). The
set is bounded on purpose: it exists to show that the warning behaviour is sensible
on clear English, clear non-English text, and text with too little language content
to judge. It is **not** an accuracy benchmark and supports no accuracy claim.

``expected`` is what the *warning policy* should conclude for the text:

- ``english``: detected as English, so no unsupported-language warning;
- ``other``: detected as a language the approved models do not support;
- ``unclear``: too little language content to judge, so "not confidently
  determined" (the person is told, and nothing is guessed).
"""

from __future__ import annotations

ENGLISH = "english"
OTHER = "other"
UNCLEAR = "unclear"

# (text, expected policy outcome)
EVAL_SET: tuple[tuple[str, str], ...] = (
    # -- clear English: support tickets, reviews, and casual posts --------------
    ("My order arrived two days late and the box was damaged.", ENGLISH),
    ("Thanks so much for the quick reply, that fixed my problem completely!", ENGLISH),
    ("I have been waiting on hold for forty minutes and nobody has picked up.", ENGLISH),
    ("The new update is great, the app feels much faster than before.", ENGLISH),
    ("Why was I charged twice for the same subscription this month?", ENGLISH),
    ("Honestly the customer service was friendlier than I expected.", ENGLISH),
    ("I can't log in anymore and the password reset email never arrives.", ENGLISH),
    ("This is the worst delivery experience I have had in years.", ENGLISH),
    ("Just wanted to say the support agent was really patient with me today.", ENGLISH),
    ("Our team is excited about the launch next week, see you all there.", ENGLISH),
    ("The refund finally showed up on my statement this morning.", ENGLISH),
    ("Can someone explain why the price went up again without any notice?", ENGLISH),
    ("lol that meme about monday meetings is painfully accurate", ENGLISH),
    ("not gonna lie, the battery life on this thing is pretty impressive", ENGLISH),
    ("Package says delivered but nothing is on my doorstep, please advise.", ENGLISH),
    ("I'm so tired of the constant notifications, how do I turn them off?", ENGLISH),
    ("What a lovely surprise to find the missing part in the second box.", ENGLISH),
    ("The checkout page keeps freezing when I try to apply a discount code.", ENGLISH),
    ("We appreciate your feedback and will pass it along to the product team.", ENGLISH),
    ("Please close my account and delete all the data you hold about me.", ENGLISH),
    ("It works, but the instructions were confusing and the manual is missing pages.", ENGLISH),
    ("Great food, slow service, and the music was way too loud for a weeknight.", ENGLISH),
    ("I'm genuinely worried about the changes to the privacy policy.", ENGLISH),
    ("Is the store open on public holidays or should I come back tomorrow?", ENGLISH),
    ("Thank you for your patience while we investigate the outage.", ENGLISH),
    ("That was the funniest thing I've seen all week, I can't stop laughing.", ENGLISH),
    ("The driver was rude and left the parcel in the rain.", ENGLISH),
    ("Dear team, I would like to request an invoice for last quarter.", ENGLISH),
    ("omg the concert last night was absolutely unreal, best night ever", ENGLISH),
    ("Nobody told me the warranty only covers the first six months.", ENGLISH),
    # -- clear non-English (several languages and scripts) ----------------------
    ("Ma commande est arrivée avec deux jours de retard et le colis était abîmé.", OTHER),
    ("Merci beaucoup pour votre réponse rapide, le problème est complètement résolu.", OTHER),
    ("Mi pedido llegó dos días tarde y la caja estaba dañada.", OTHER),
    ("Muchas gracias por la ayuda, el servicio de atención fue muy amable.", OTHER),
    ("Meine Bestellung ist zwei Tage zu spät angekommen und der Karton war beschädigt.", OTHER),
    ("Vielen Dank für die schnelle Antwort, das Problem ist jetzt gelöst.", OTHER),
    ("Il mio ordine è arrivato con due giorni di ritardo e la scatola era rovinata.", OTHER),
    ("Grazie mille per la risposta veloce, il problema è stato risolto.", OTHER),
    ("O meu pedido chegou com dois dias de atraso e a caixa estava danificada.", OTHER),
    ("Obrigado pela ajuda rápida, o atendimento foi excelente.", OTHER),
    ("Mijn bestelling kwam twee dagen te laat aan en de doos was beschadigd.", OTHER),
    ("Hartelijk dank voor uw snelle antwoord, het probleem is opgelost.", OTHER),
    ("Min beställning kom två dagar för sent och kartongen var skadad.", OTHER),
    ("Moje zamówienie dotarło dwa dni później, a paczka była uszkodzona.", OTHER),
    ("Siparişim iki gün geç geldi ve kutu hasarlıydı, çok memnun kalmadım.", OTHER),
    ("Мой заказ пришёл на два дня позже, а коробка была повреждена.", OTHER),
    ("Дякую за швидку відповідь, проблему повністю вирішено.", OTHER),
    ("وصل طلبي متأخرا بيومين وكان الصندوق تالفا.", OTHER),
    ("شكرا جزيلا على المساعدة السريعة، كانت الخدمة ممتازة.", OTHER),
    ("ההזמנה שלי הגיעה באיחור של יומיים והקופסה הייתה פגומה.", OTHER),
    ("我的订单晚了两天才到，而且包装箱已经损坏了。", OTHER),
    ("非常感谢你们的快速回复，问题已经完全解决了。", OTHER),
    ("注文が二日遅れて届き、箱も傷んでいました。", OTHER),
    ("迅速なご対応をありがとうございました。問題は解決しました。", OTHER),
    ("주문한 상품이 이틀 늦게 도착했고 상자도 파손되어 있었습니다.", OTHER),
    ("빠른 답변 정말 감사합니다. 문제가 완전히 해결되었어요.", OTHER),
    ("मेरा ऑर्डर दो दिन देर से पहुंचा और डिब्बा भी टूटा हुआ था।", OTHER),
    ("ฉันได้รับพัสดุช้าไปสองวันและกล่องก็เสียหาย", OTHER),
    ("Đơn hàng của tôi đến muộn hai ngày và hộp bị hư hỏng.", OTHER),
    ("Pesanan saya tiba terlambat dua hari dan kotaknya rusak.", OTHER),
    ("Terima kasih banyak atas bantuan cepatnya, layanannya sangat baik.", OTHER),
    ("Η παραγγελία μου έφτασε με δύο μέρες καθυστέρηση και το κουτί ήταν κατεστραμμένο.", OTHER),
    # -- too little language content to judge -----------------------------------
    ("ok", UNCLEAR),
    ("lol", UNCLEAR),
    ("🙂🙂🙂", UNCLEAR),
    ("😡😡😡!!!", UNCLEAR),
    ("12345 67890", UNCLEAR),
    ("https://example.com/a/b?c=d", UNCLEAR),
    ("@someone #topic", UNCLEAR),
    ("!!!???", UNCLEAR),
    ("...", UNCLEAR),
    ("haha", UNCLEAR),
    ("a", UNCLEAR),
    ("ID-4821-X", UNCLEAR),
)
