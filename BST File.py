import struct
import csv
import os

# Formato del registro: ID, Nombre, Cantidad, Precio, Fecha, left, right
FORMAT = 'i30sif10sii'
HEADER_FORMAT = 'i'  # Cantidad de registros
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECORD_SIZE = struct.calcsize(FORMAT)

class Venta:
    def __init__(self, id_venta, nombre_producto, cantidad_vendida, precio_unitario, fecha_venta, left=-1, right=-1):
        self.id_venta = id_venta
        self.nombre_producto = nombre_producto.encode('utf-8')[:30].ljust(30, b' ')
        self.cantidad_vendida = cantidad_vendida
        self.precio_unitario = precio_unitario
        self.fecha_venta = fecha_venta.encode('utf-8')[:10].ljust(10, b' ')
        self.left = left
        self.right = right

    def __str__(self):
        return (f"ID Venta: {self.id_venta} | Producto: {self.nombre_producto.decode().strip()} "
                f"| Cantidad: {self.cantidad_vendida} | Precio: {self.precio_unitario} "
                f"| Fecha: {self.fecha_venta.decode().strip()} | left: {self.left} | right: {self.right}")

class BSTFile:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(filename):
            with open(filename, 'wb') as f:
                f.write(struct.pack(HEADER_FORMAT, 0))  # Inicializa con 0 registros

    def insert(self, venta):
        with open(self.filename, 'r+b') as f:
            f.seek(0)
            count = struct.unpack(HEADER_FORMAT, f.read(HEADER_SIZE))[0]

            if count == 0:
                f.seek(HEADER_SIZE)
                f.write(struct.pack(FORMAT, venta.id_venta, venta.nombre_producto, venta.cantidad_vendida,
                                venta.precio_unitario, venta.fecha_venta, -1, -1))
                f.seek(0)
                f.write(struct.pack(HEADER_FORMAT, 1))
                return

            pos = HEADER_SIZE
            while True:
                f.seek(pos)
                data = f.read(RECORD_SIZE)
                if len(data) < RECORD_SIZE:
                    break  # archivo corrupto o fin inesperado

                current = struct.unpack(FORMAT, data)
                current_id, _, _, _, _, left, right = current

                if venta.id_venta < current_id:
                    if left == -1:
                        f.seek(pos + RECORD_SIZE - 8)  # campo `left`
                        f.write(struct.pack('i', count))
                        break
                    else:
                        pos = HEADER_SIZE + left * RECORD_SIZE
                else:
                    if right == -1:
                        f.seek(pos + RECORD_SIZE - 4)  # campo `right`
                        f.write(struct.pack('i', count))
                        break
                    else:
                        pos = HEADER_SIZE + right * RECORD_SIZE

            # Insertar nuevo nodo al final
            f.seek(HEADER_SIZE + count * RECORD_SIZE)
            f.write(struct.pack(FORMAT, venta.id_venta, venta.nombre_producto, venta.cantidad_vendida,
                                venta.precio_unitario, venta.fecha_venta, -1, -1))
            f.seek(0)
            f.write(struct.pack(HEADER_FORMAT, count + 1))


    def leer(self):
        ventas = []
        with open(self.filename, 'rb') as f:
            count_bytes = f.read(HEADER_SIZE)
            if len(count_bytes) < HEADER_SIZE:
                return ventas  # archivo vacío

            count = struct.unpack(HEADER_FORMAT, count_bytes)[0]

            for i in range(count):
                f.seek(HEADER_SIZE + i * RECORD_SIZE)
                data = f.read(RECORD_SIZE)
                if len(data) < RECORD_SIZE:
                    continue  # registro incompleto

                try:
                    unpacked = struct.unpack(FORMAT, data)
                    venta = Venta(
                        unpacked[0],
                        unpacked[1].decode('utf-8', errors='ignore').strip(),
                        unpacked[2],
                        unpacked[3],
                        unpacked[4].decode('utf-8', errors='ignore').strip(),
                        unpacked[5],
                        unpacked[6]
                    )
                    ventas.append(venta)
                except struct.error:
                    continue  # ignora errores al desempaquetar
        return ventas



    def search(self, key):
        with open(self.filename, 'rb') as f:
            f.seek(0)
            count = struct.unpack(HEADER_FORMAT, f.read(HEADER_SIZE))[0]
            pos = HEADER_SIZE

            while True:
                if pos >= HEADER_SIZE + count * RECORD_SIZE:
                    return None  # no encontrado

                f.seek(pos)
                data = f.read(RECORD_SIZE)
                if len(data) < RECORD_SIZE:
                    return None

                unpacked = struct.unpack(FORMAT, data)
                id_venta, nombre, cantidad, precio, fecha, left, right = unpacked

                if id_venta == -1:
                    return None  # eliminado

                if key == id_venta:
                    return Venta(id_venta, nombre.decode().strip(), cantidad, precio, fecha.decode().strip(), left, right)

                if key < id_venta:
                    if left == -1:
                        return None
                    pos = HEADER_SIZE + left * RECORD_SIZE
                else:
                    if right == -1:
                        return None
                    pos = HEADER_SIZE + right * RECORD_SIZE

    def remove(self, key):
        with open(self.filename, 'r+b') as f:
            f.seek(0)
            count = struct.unpack(HEADER_FORMAT, f.read(HEADER_SIZE))[0]
            pos = HEADER_SIZE

            while True:
                if pos >= HEADER_SIZE + count * RECORD_SIZE:
                    return False

                f.seek(pos)
                data = f.read(RECORD_SIZE)
                if len(data) < RECORD_SIZE:
                    return False

                unpacked = struct.unpack(FORMAT, data)
                id_venta, _, _, _, _, left, right = unpacked

                if key == id_venta:
                    f.seek(pos)
                    f.write(struct.pack('i', -1))  # marcar como eliminado
                    return True

                if key < id_venta:
                    if left == -1:
                        return False
                    pos = HEADER_SIZE + left * RECORD_SIZE
                else:
                    if right == -1:
                        return False
                    pos = HEADER_SIZE + right * RECORD_SIZE

    def rangeSearch(self, init_key, end_key):
        resultados = []

        def in_order(pos):
            with open(self.filename, 'rb') as f:
                if pos == -1:
                    return
                f.seek(pos)
                data = f.read(RECORD_SIZE)
                if not data:
                    return
                unpacked = struct.unpack(FORMAT, data)
                id_venta, nombre, cantidad, precio, fecha, left, right = unpacked
                if id_venta == -1:
                    return

                if left != -1:
                    in_order(HEADER_SIZE + left * RECORD_SIZE)

                if init_key <= id_venta <= end_key:
                    venta = Venta(id_venta, nombre.decode().strip(), cantidad, precio, fecha.decode().strip(), left, right)
                    resultados.append(venta)

                if right != -1:
                    in_order(HEADER_SIZE + right * RECORD_SIZE)

        in_order(HEADER_SIZE)
        return resultados

if __name__ == "__main__":
    archivo = BSTFile("ventas.dat")

    # Insertar ventas
    archivo.insert(Venta(1, "Producto A", 10, 5.5, "2024-07-01"))
    archivo.insert(Venta(2, "Producto B", 5, 10.0, "2024-07-02"))
    archivo.insert(Venta(3, "Producto C", 7, 8.75, "2024-07-03"))

    # Leer todas las ventas
    print("Ventas registradas:")
    for venta in archivo.leer():
        print(venta)

    # Buscar una venta específica
    print("\nBuscando venta con ID 2:")
    resultado = archivo.search(2)
    print(resultado if resultado else "No encontrada")

    # Eliminar una venta
    print("\nEliminando venta con ID 2")
    archivo.remove(2)

    # Verificar eliminación
    print("\nVentas después de eliminación:")
    for venta in archivo.leer():
        print(venta)

    # Búsqueda por rango
    print("\nBuscando ventas con ID entre 1 y 3:")
    for venta in archivo.rangeSearch(1, 3):
        print(venta)
