"""
Modulo de impressao Bluetooth ESC/POS
Compativel com Kapbom KA-1444 (58mm)
Usa jnius para acessar APIs nativas do Android
"""

# Comandos ESC/POS para impressora termica 58mm
ESC = b'\x1b'
GS  = b'\x1d'

CMD_INIT        = ESC + b'\x40'           # Inicializar impressora
CMD_BOLD_ON     = ESC + b'\x45\x01'       # Negrito ligado
CMD_BOLD_OFF    = ESC + b'\x45\x00'       # Negrito desligado
CMD_ALIGN_LEFT  = ESC + b'\x61\x00'       # Alinhar esquerda
CMD_ALIGN_CENTER= ESC + b'\x61\x01'       # Alinhar centro
CMD_ALIGN_RIGHT = ESC + b'\x61\x02'       # Alinhar direita
CMD_FONT_NORMAL = ESC + b'\x21\x00'       # Fonte normal
CMD_FONT_LARGE  = ESC + b'\x21\x30'       # Fonte grande (2x)
CMD_FONT_MEDIUM = ESC + b'\x21\x10'       # Fonte media (altura dupla)
CMD_CUT         = GS  + b'\x56\x41\x00'  # Cortar papel (parcial)
CMD_FEED        = b'\x0a'                 # Avancar linha
CMD_FEED3       = b'\x0a\x0a\x0a'        # Avancar 3 linhas

LINHA_SIMPLES = b'-' * 32 + b'\n'
LINHA_DUPLA   = b'=' * 32 + b'\n'

BLUETOOTH_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # SPP padrao


def _get_bluetooth_socket(mac_address):
    """
    Cria e retorna um socket Bluetooth conectado ao MAC informado.
    Usa jnius para acessar BluetoothAdapter do Android.
    """
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        BluetoothDevice  = autoclass('android.bluetooth.BluetoothDevice')
        UUID             = autoclass('java.util.UUID')

        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None:
            print("[BT] Bluetooth nao disponivel neste dispositivo")
            return None

        if not adapter.isEnabled():
            print("[BT] Bluetooth esta desativado")
            return None

        device = adapter.getRemoteDevice(mac_address.upper())
        uuid   = UUID.fromString(BLUETOOTH_UUID)
        socket = device.createRfcommSocketToServiceRecord(uuid)

        adapter.cancelDiscovery()
        socket.connect()
        print(f"[BT] Conectado em {mac_address}")
        return socket

    except Exception as e:
        print(f"[BT] Erro ao conectar: {e}")
        return None


def _encode_texto(texto):
    """
    Codifica texto para bytes compativel com impressora termica.
    Remove acentos problematicos e converte para latin-1.
    """
    substituicoes = {
        'ã': 'a', 'â': 'a', 'á': 'a', 'à': 'a', 'ä': 'a',
        'ê': 'e', 'é': 'e', 'è': 'e', 'ë': 'e',
        'î': 'i', 'í': 'i', 'ì': 'i', 'ï': 'i',
        'õ': 'o', 'ô': 'o', 'ó': 'o', 'ò': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Ã': 'A', 'Â': 'A', 'Á': 'A', 'À': 'A',
        'Ê': 'E', 'É': 'E', 'È': 'E',
        'Î': 'I', 'Í': 'I',
        'Õ': 'O', 'Ô': 'O', 'Ó': 'O',
        'Ú': 'U', 'Û': 'U',
        'Ç': 'C',
    }
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return texto.encode('ascii', errors='replace')


def montar_comanda(pedido):
    """
    Monta os bytes ESC/POS da comanda completa a partir do dict do pedido.
    """
    import json as _json
    from datetime import datetime

    buf = bytearray()

    def w(b):
        buf.extend(b)

    def linha(texto='', bold=False, center=False, large=False):
        if center:
            w(CMD_ALIGN_CENTER)
        else:
            w(CMD_ALIGN_LEFT)
        if large:
            w(CMD_FONT_LARGE)
        elif bold:
            w(CMD_BOLD_ON)
        w(_encode_texto(str(texto)))
        w(b'\n')
        if large:
            w(CMD_FONT_NORMAL)
        elif bold:
            w(CMD_BOLD_OFF)
        w(CMD_ALIGN_LEFT)

    # --- Cabecalho ---
    w(CMD_INIT)
    w(CMD_ALIGN_CENTER)
    w(CMD_FONT_LARGE)
    w(_encode_texto('SALDATERRA'))
    w(b'\n')
    w(CMD_FONT_NORMAL)
    w(CMD_ALIGN_LEFT)
    w(LINHA_DUPLA)

    # Numero do pedido
    num = pedido.get('numero_pedido', '---')
    w(CMD_ALIGN_CENTER)
    w(CMD_BOLD_ON)
    w(CMD_FONT_MEDIUM)
    w(_encode_texto(f'PEDIDO #{num}'))
    w(b'\n')
    w(CMD_FONT_NORMAL)
    w(CMD_BOLD_OFF)
    w(CMD_ALIGN_LEFT)

    # Data/hora
    try:
        dt = pedido.get('created_at', '')
        if dt:
            dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            dt_str = dt_obj.strftime('%d/%m/%Y %H:%M')
        else:
            dt_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    except Exception:
        dt_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    w(CMD_ALIGN_CENTER)
    w(_encode_texto(dt_str))
    w(b'\n')
    w(CMD_ALIGN_LEFT)
    w(LINHA_SIMPLES)

    # --- Cliente ---
    linha('CLIENTE:', bold=True)
    linha(pedido.get('cliente_nome', 'Nao informado'))

    tel = pedido.get('cliente_telefone', '')
    if tel:
        linha(f'Tel: {tel}')

    endereco = pedido.get('endereco_entrega', '')
    bairro   = pedido.get('bairro', '')
    if endereco:
        linha(f'End: {endereco}')
    if bairro:
        linha(f'Bairro: {bairro}')

    w(LINHA_SIMPLES)

    # --- Itens ---
    linha('ITENS DO PEDIDO:', bold=True)
    w(b'\n')

    itens = pedido.get('itens', [])
    if isinstance(itens, str):
        try:
            itens = _json.loads(itens)
        except Exception:
            itens = []

    if itens:
        for item in itens:
            nome  = item.get('nome', item.get('name', '?'))
            qtd   = item.get('quantidade', item.get('qty', item.get('quantity', 1)))
            preco = item.get('preco_unitario', item.get('price', item.get('preco', 0)))
            obs   = item.get('observacao', item.get('obs', ''))

            subtotal = float(qtd) * float(preco)
            linha_item = f'{qtd}x {nome}'
            # Linha com nome e preco
            espaco = 32 - len(linha_item) - len(f'R${subtotal:.2f}')
            if espaco < 1:
                espaco = 1
            w(CMD_BOLD_ON)
            w(_encode_texto(linha_item))
            w(CMD_BOLD_OFF)
            w(_encode_texto(' ' * espaco + f'R${subtotal:.2f}'))
            w(b'\n')

            if obs:
                linha(f'  >> {obs}')
    else:
        linha('(sem itens registrados)')

    w(b'\n')
    w(LINHA_SIMPLES)

    # --- Totais ---
    taxa = float(pedido.get('taxa_entrega', 0))
    total = float(pedido.get('valor_total', 0))

    if taxa > 0:
        esp = 32 - len('Taxa entrega:') - len(f'R${taxa:.2f}')
        w(_encode_texto('Taxa entrega:' + ' ' * esp + f'R${taxa:.2f}'))
        w(b'\n')

    esp = 32 - len('TOTAL:') - len(f'R${total:.2f}')
    w(CMD_BOLD_ON)
    w(CMD_FONT_MEDIUM)
    w(_encode_texto('TOTAL:' + ' ' * esp + f'R${total:.2f}'))
    w(b'\n')
    w(CMD_FONT_NORMAL)
    w(CMD_BOLD_OFF)

    # Forma de pagamento
    forma = pedido.get('forma_pagamento', '')
    if forma:
        linha(f'Pagamento: {forma}')

    w(LINHA_DUPLA)
    w(CMD_ALIGN_CENTER)
    w(_encode_texto('Obrigado pela preferencia!'))
    w(b'\n')
    w(CMD_ALIGN_LEFT)
    w(CMD_FEED3)
    w(CMD_CUT)

    return bytes(buf)


def imprimir_pedido(mac_address, pedido):
    """
    Funcao principal: conecta via Bluetooth e imprime a comanda.
    Retorna True se imprimiu com sucesso, False caso contrario.
    """
    if not mac_address or len(mac_address) != 17:
        print("[BT] MAC address invalido")
        return False

    dados = montar_comanda(pedido)
    socket = _get_bluetooth_socket(mac_address)

    if socket is None:
        return False

    try:
        stream = socket.getOutputStream()
        stream.write(dados)
        stream.flush()
        print(f"[BT] Comanda impressa! Pedido #{pedido.get('numero_pedido', '?')}")
        return True
    except Exception as e:
        print(f"[BT] Erro ao enviar dados: {e}")
        return False
    finally:
        try:
            socket.close()
        except Exception:
            pass


def listar_dispositivos_pareados():
    """
    Retorna lista de dispositivos Bluetooth pareados no celular.
    Formato: [{'nome': str, 'mac': str}, ...]
    """
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None or not adapter.isEnabled():
            return []

        devices = adapter.getBondedDevices().toArray()
        result = []
        for d in devices:
            result.append({
                'nome': d.getName() or 'Desconhecido',
                'mac':  d.getAddress()
            })
        return result
    except Exception as e:
        print(f"[BT] Erro ao listar dispositivos: {e}")
        return []
