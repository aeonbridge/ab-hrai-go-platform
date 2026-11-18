/* Evento em curso. A sala fixa reúne todos os celulares que chegam sem ?sala= (por exemplo, pelo link curto),
   e o QR code mostra o link curto quando o telão estiver nessa sala.
   O link curto deve redirecionar para: https://hrai-go.aeonbridge.io/?sala=ai-ethic-br#participar
   (o endereço antigo aeonbridge.github.io/ab-hrai-go-platform/ redireciona para o domínio próprio) */
window.HRAIGO_EVENTO = { sala: "ai-ethic-br", linkPublico: "https://go.aeonbridge.io/ai-ethic-br" };
