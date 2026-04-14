"""
SALDATERRA — Impressora Bluetooth Android
Imprime comandas automaticamente via Bluetooth (Kapbom KA-1444)
Monitora novos pedidos no Supabase em segundo plano com Foreground Service
"""

import threading
import time
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.utils import platform

import supabase_client as db
import bluetooth_printer as bt

# ── Cores ──────────────────────────────────────────────────
COR_LARANJA  = (1, 0.48, 0, 1)
COR_FUNDO    = (0.07, 0.07, 0.10, 1)
COR_CARD     = (0.12, 0.12, 0.17, 1)
COR_VERDE    = (0.13, 0.76, 0.37, 1)
COR_VERMELHO = (0.90, 0.25, 0.25, 1)
COR_TEXTO    = (1, 1, 1, 1)
COR_CINZA    = (0.55, 0.55, 0.55, 1)
COR_AMARELO  = (1, 0.85, 0.0, 1)

Window.clearcolor = COR_FUNDO


def salvar_config(mac, intervalo):
    try:
        with open('config.json', 'w') as f:
            json.dump({'mac': mac, 'intervalo': intervalo}, f)
    except Exception:
        pass


def carregar_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {'mac': '', 'intervalo': 10}


def iniciar_foreground_service():
    """
    Inicia Foreground Service no Android para rodar em 2o plano sem ser morto.
    Aparece uma notificação persistente enquanto ativo.
    """
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        from android import mActivity

        Context        = autoclass('android.content.Context')
        Intent         = autoclass('android.content.Intent')
        NotifManager   = autoclass('android.app.NotificationManager')
        NotifChannel   = autoclass('android.app.NotificationChannel')
        NotifCompat    = autoclass('androidx.core.app.NotificationCompat')
        NotifBuilder   = autoclass('androidx.core.app.NotificationCompat$Builder')
        ServiceClass   = autoclass('android.app.Service')

        CHANNEL_ID   = "saldaterra_canal"
        CHANNEL_NAME = "Saldaterra Impressora"
        NOTIF_ID     = 1001

        activity = mActivity

        # Criar canal de notificação (Android 8+)
        nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        ch = NotifChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotifManager.IMPORTANCE_LOW
        )
        ch.setDescription("Monitoramento de pedidos em segundo plano")
        nm.createNotificationChannel(ch)

        # Construir notificação
        builder = NotifCompat.Builder(activity, CHANNEL_ID)
        builder.setSmallIcon(activity.getApplicationInfo().icon)
        builder.setContentTitle("Saldaterra - Monitorando")
        builder.setContentText("Aguardando novos pedidos para imprimir...")
        builder.setPriority(NotifCompat.PRIORITY_LOW)
        builder.setOngoing(True)
        builder.setAutoCancel(False)

        notif = builder.build()
        nm.notify(NOTIF_ID, notif)

        print("[Service] Foreground service iniciado!")
    except Exception as e:
        print(f"[Service] Erro ao iniciar foreground service: {e}")


def parar_foreground_service():
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        from android import mActivity

        Context      = autoclass('android.content.Context')
        NotifManager = autoclass('android.app.NotificationManager')
        NOTIF_ID     = 1001

        nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
        nm.cancel(NOTIF_ID)
        print("[Service] Foreground service parado.")
    except Exception as e:
        print(f"[Service] Erro ao parar service: {e}")


class StatusBar(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=36, padding=(8, 4), spacing=8, **kw)
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*COR_CARD)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        self.dot = Label(text='●', font_size='18sp', size_hint_x=None,
                         width=24, color=COR_CINZA)
        self.txt = Label(text='Parado', font_size='13sp', color=COR_CINZA,
                         halign='left', valign='middle')
        self.txt.bind(size=self.txt.setter('text_size'))
        self.add_widget(self.dot)
        self.add_widget(self.txt)

    def _upd(self, *a):
        self._rect.pos  = self.pos
        self._rect.size = self.size

    def set_status(self, texto, cor):
        self.dot.color = cor
        self.txt.color = cor
        self.txt.text  = texto


class LogBox(ScrollView):
    def __init__(self, **kw):
        super().__init__(size_hint=(1, 1), **kw)
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None,
                                spacing=2, padding=4)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)
        self._linhas = []

    def adicionar(self, texto, cor=None):
        cor = cor or COR_TEXTO
        from datetime import datetime
        hora = datetime.now().strftime('%H:%M:%S')
        lbl = Label(text=f'[{hora}] {texto}', font_size='12sp',
                    color=cor, size_hint_y=None, height=22,
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        self.layout.add_widget(lbl)
        self._linhas.append(lbl)
        if len(self._linhas) > 50:
            old = self._linhas.pop(0)
            self.layout.remove_widget(old)
        Clock.schedule_once(lambda dt: setattr(self, 'scroll_y', 0), 0.1)


class MainLayout(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', spacing=8,
                         padding=(12, 8, 12, 12), **kw)
        cfg = carregar_config()
        self.mac_impressora = cfg.get('mac', '')
        self.intervalo      = cfg.get('intervalo', 10)
        self.rodando        = False
        self._thread        = None
        self._pedidos_impressos = set()
        self._contador      = 0

        self._build_ui()
        Clock.schedule_once(lambda dt: self._verificar_banco(), 2)

    def _build_ui(self):
        # Título
        tit = Label(text='🖨  SALDATERRA', font_size='22sp',
                    bold=True, color=COR_LARANJA,
                    size_hint_y=None, height=44)
        self.add_widget(tit)

        sub = Label(text='Impressora Bluetooth Automática',
                    font_size='13sp', color=COR_CINZA,
                    size_hint_y=None, height=22)
        self.add_widget(sub)

        # Status bar
        self.status_bar = StatusBar()
        self.add_widget(self.status_bar)

        # Aviso foreground service
        self.lbl_aviso = Label(
            text='⚠  Inicie o monitoramento para manter ativo em 2° plano',
            font_size='11sp', color=COR_AMARELO,
            size_hint_y=None, height=20, halign='center'
        )
        self.lbl_aviso.bind(size=self.lbl_aviso.setter('text_size'))
        self.add_widget(self.lbl_aviso)

        # ── Config box ──────────────────────────────────────
        cfg_box = BoxLayout(orientation='vertical', size_hint_y=None,
                            height=130, spacing=6)
        with cfg_box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*COR_CARD)
            self._cfg_rect = RoundedRectangle(pos=cfg_box.pos,
                                               size=cfg_box.size, radius=[8])
        cfg_box.bind(
            pos=lambda *a: setattr(self._cfg_rect, 'pos', cfg_box.pos),
            size=lambda *a: setattr(self._cfg_rect, 'size', cfg_box.size)
        )

        # MAC
        row_mac = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=40, spacing=6, padding=(8, 4))
        row_mac.add_widget(Label(text='MAC:', font_size='13sp',
                                  color=COR_TEXTO, size_hint_x=None, width=40))
        self.mac_input = TextInput(
            text=self.mac_impressora,
            hint_text='Ex: 00:11:22:33:AA:BB',
            font_size='13sp', multiline=False,
            background_color=(0.18, 0.18, 0.25, 1),
            foreground_color=COR_TEXTO
        )
        self.mac_input.bind(text=self._on_mac_change)

        btn_buscar = Button(text='📡 Buscar', font_size='12sp',
                             size_hint_x=None, width=90,
                             background_color=(0.2, 0.3, 0.6, 1))
        btn_buscar.bind(on_press=self._buscar_dispositivos)

        row_mac.add_widget(self.mac_input)
        row_mac.add_widget(btn_buscar)
        cfg_box.add_widget(row_mac)

        # Intervalo
        row2 = BoxLayout(orientation='horizontal', size_hint_y=None,
                         height=40, spacing=6, padding=(8, 4))
        row2.add_widget(Label(text='Intervalo:', font_size='13sp',
                               color=COR_TEXTO, size_hint_x=None, width=70))
        self.spin_intervalo = Spinner(
            text=str(self.intervalo),
            values=['5', '10', '15', '30', '60'],
            font_size='13sp', size_hint_x=None, width=70,
            background_color=(0.18, 0.18, 0.25, 1)
        )
        self.spin_intervalo.bind(text=self._on_intervalo_change)
        row2.add_widget(self.spin_intervalo)
        row2.add_widget(Label(text='seg', font_size='12sp', color=COR_CINZA,
                               size_hint_x=None, width=30))
        btn_testar = Button(text='🔗 Testar Supabase', font_size='12sp',
                             background_color=(0.25, 0.25, 0.35, 1))
        btn_testar.bind(on_press=self._testar_conexao)
        row2.add_widget(btn_testar)
        cfg_box.add_widget(row2)

        # Botão teste impressora
        row3 = BoxLayout(orientation='horizontal', size_hint_y=None,
                         height=36, spacing=6, padding=(8, 2))
        btn_teste_imp = Button(text='🖨  Imprimir Teste', font_size='12sp',
                                background_color=(0.3, 0.2, 0.5, 1))
        btn_teste_imp.bind(on_press=self._imprimir_teste)
        row3.add_widget(btn_teste_imp)
        cfg_box.add_widget(row3)

        self.add_widget(cfg_box)

        # Botão INICIAR / PARAR
        self.btn_toggle = Button(
            text='▶  INICIAR MONITORAMENTO',
            font_size='16sp', bold=True,
            size_hint_y=None, height=56,
            background_color=COR_VERDE
        )
        self.btn_toggle.bind(on_press=self._toggle_servico)
        self.add_widget(self.btn_toggle)

        # Contador
        self.lbl_contador = Label(
            text='Pedidos impressos: 0',
            font_size='13sp', color=COR_CINZA,
            size_hint_y=None, height=24
        )
        self.add_widget(self.lbl_contador)

        # Log
        self.add_widget(Label(text='Log de atividades:', font_size='12sp',
                               color=COR_CINZA, size_hint_y=None, height=20,
                               halign='left'))
        self.log = LogBox()
        self.add_widget(self.log)

    # ── Event handlers ─────────────────────────────────────

    def _on_mac_change(self, inst, val):
        self.mac_impressora = val.strip()
        salvar_config(self.mac_impressora, self.intervalo)

    def _on_intervalo_change(self, inst, val):
        try:
            self.intervalo = int(val)
            salvar_config(self.mac_impressora, self.intervalo)
        except Exception:
            pass

    def _buscar_dispositivos(self, *a):
        self.log_info('Buscando dispositivos pareados...')
        def _run():
            devices = bt.listar_dispositivos_pareados()
            if not devices:
                self.log_erro('Nenhum dispositivo pareado encontrado.')
                self.log_info('Pareie a KA-1444 nas configurações de Bluetooth do celular!')
                return
            self._mostrar_popup_dispositivos(devices)
        threading.Thread(target=_run, daemon=True).start()

    @mainthread
    def _mostrar_popup_dispositivos(self, devices):
        content = BoxLayout(orientation='vertical', spacing=8, padding=12)
        content.add_widget(Label(text='Selecione a impressora:',
                                  font_size='14sp', size_hint_y=None, height=30))
        popup = Popup(title='Dispositivos Bluetooth',
                      content=content, size_hint=(0.9, 0.75))
        for d in devices:
            btn = Button(text=f"{d['nome']}\n{d['mac']}",
                          font_size='13sp', size_hint_y=None, height=60)
            mac = d['mac']
            def _sel(inst, m=mac):
                self.mac_input.text = m
                self.log_ok(f'Impressora selecionada: {m}')
                popup.dismiss()
            btn.bind(on_press=_sel)
            content.add_widget(btn)
        popup.open()

    def _testar_conexao(self, *a):
        self.log_info('Testando conexão com Supabase...')
        def _run():
            ok = db.testar_conexao()
            if ok:
                self.log_ok('✅ Supabase conectado!')
            else:
                self.log_erro('❌ Falha no Supabase. Verifique a internet.')
        threading.Thread(target=_run, daemon=True).start()

    def _imprimir_teste(self, *a):
        mac = self.mac_impressora
        if not mac:
            self.log_erro('Configure o MAC da impressora primeiro!')
            return
        pedido_teste = {
            'numero_pedido': 'TESTE',
            'cliente_nome': 'Cliente Teste',
            'cliente_telefone': '(81) 99999-9999',
            'endereco_entrega': 'Rua Teste, 123',
            'bairro': 'Centro',
            'itens': [
                {'nome': 'X-Burguer Especial', 'quantidade': 2, 'preco_unitario': 18.50, 'observacao': 'sem cebola'},
                {'nome': 'Coca-Cola 350ml', 'quantidade': 1, 'preco_unitario': 6.00}
            ],
            'forma_pagamento': 'PIX',
            'valor_total': 43.00,
            'taxa_entrega': 5.00,
        }
        self.log_info(f'Enviando teste para {mac}...')
        def _run():
            ok = bt.imprimir_pedido(mac, pedido_teste)
            if ok:
                self.log_ok('✅ Impressão de teste enviada!')
            else:
                self.log_erro('❌ Falha na impressão. Verifique Bluetooth e MAC.')
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_servico(self, *a):
        if self.rodando:
            self._parar()
        else:
            self._iniciar()

    def _iniciar(self):
        if not self.mac_impressora:
            self.log_erro('Configure o MAC da impressora antes de iniciar!')
            return
        self.rodando = True
        self.btn_toggle.text = '⏹  PARAR MONITORAMENTO'
        self.btn_toggle.background_color = COR_VERMELHO
        self.status_bar.set_status(f'Monitorando... (a cada {self.intervalo}s)', COR_VERDE)
        self.lbl_aviso.text = '✅  Rodando em 2° plano. Pode minimizar o app!'
        self.lbl_aviso.color = COR_VERDE
        self.log_ok(f'Monitoramento iniciado! Intervalo: {self.intervalo}s')
        self.log_info(f'Impressora: {self.mac_impressora}')
        self._manter_tela_ligada(True)
        iniciar_foreground_service()
        self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True)
        self._thread.start()

    def _parar(self):
        self.rodando = False
        self.btn_toggle.text = '▶  INICIAR MONITORAMENTO'
        self.btn_toggle.background_color = COR_VERDE
        self.status_bar.set_status('Parado', COR_CINZA)
        self.lbl_aviso.text = '⚠  Inicie o monitoramento para manter ativo em 2° plano'
        self.lbl_aviso.color = COR_AMARELO
        self.log_info('Monitoramento pausado.')
        self._manter_tela_ligada(False)
        parar_foreground_service()

    def _loop_monitoramento(self):
        """Loop principal em thread separada — roda enquanto self.rodando=True."""
        consecutivos_erro = 0
        while self.rodando:
            try:
                pedidos = db.buscar_pedidos_novos()
                consecutivos_erro = 0

                for pedido in pedidos:
                    if not self.rodando:
                        return
                    pid = pedido.get('id')
                    if pid in self._pedidos_impressos:
                        continue

                    num = pedido.get('numero_pedido', '?')
                    self.log_info(f'Novo pedido #{num} recebido!')

                    ok = bt.imprimir_pedido(self.mac_impressora, pedido)
                    if ok:
                        self._pedidos_impressos.add(pid)
                        db.marcar_como_impresso(pid)
                        self._contador += 1
                        self.log_ok(f'✅ Pedido #{num} impresso com sucesso!')
                        self._atualizar_contador()
                    else:
                        self.log_erro(f'❌ Falha ao imprimir pedido #{num}')

            except Exception as e:
                consecutivos_erro += 1
                self.log_erro(f'Erro: {e}')
                if consecutivos_erro >= 5:
                    self.log_erro('Muitos erros consecutivos. Verifique conexão.')
                    consecutivos_erro = 0

            # Aguarda intervalo configurado
            for _ in range(self.intervalo * 2):
                if not self.rodando:
                    return
                time.sleep(0.5)

    @mainthread
    def _atualizar_contador(self):
        self.lbl_contador.text = f'Pedidos impressos: {self._contador}'

    @mainthread
    def log_info(self, txt):
        self.log.adicionar(txt, COR_CINZA)

    @mainthread
    def log_ok(self, txt):
        self.log.adicionar(txt, COR_VERDE)

    @mainthread
    def log_erro(self, txt):
        self.log.adicionar(txt, COR_VERMELHO)

    def _manter_tela_ligada(self, ativo):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            WM = autoclass('android.view.WindowManager$LayoutParams')
            if ativo:
                activity.getWindow().addFlags(WM.FLAG_KEEP_SCREEN_ON)
            else:
                activity.getWindow().clearFlags(WM.FLAG_KEEP_SCREEN_ON)
        except Exception:
            pass

    def _verificar_banco(self):
        self.log_info('Verificando banco de dados...')
        def _run():
            resultado = db._request('GET', 'pedidos?select=impresso&limit=1')
            if resultado is None:
                self.log_erro('⚠  Coluna "impresso" nao existe no banco!')
                self.log_info('Execute no Supabase SQL Editor:')
                self.log_info('ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS impresso BOOLEAN DEFAULT FALSE;')
            else:
                self.log_ok('✅ Banco configurado corretamente!')
                self.log_info('Pronto. Configure o MAC e clique em INICIAR.')
        threading.Thread(target=_run, daemon=True).start()


class SaldaterraApp(App):
    def build(self):
        self.title = 'Saldaterra Impressora'
        return MainLayout()

    def on_pause(self):
        # Permite minimizar sem fechar — ESSENCIAL para 2° plano
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        parar_foreground_service()


if __name__ == '__main__':
    SaldaterraApp().run()
