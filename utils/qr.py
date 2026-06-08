import os
import qrcode

QR_FOLDER = "static/qr"

os.makedirs(QR_FOLDER, exist_ok=True)


def generar_qr(token):

    ruta = os.path.join(
        QR_FOLDER,
        f"{token}.png"
    )

    
    if os.path.exists(ruta):
        return ruta

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )

    qr.add_data(token)

    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    img.save(ruta)

    return ruta