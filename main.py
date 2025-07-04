import sys
import os
import subprocess
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QMessageBox,
    QLabel, QTabWidget, QVBoxLayout, QTextEdit, QSizePolicy, QLineEdit, QHBoxLayout
)
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
from PyQt5.QtCore import Qt


class PartitionMapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.partitions = []  # List of tuples (partition_number, size_mb)

    def update_partitions(self, partitions):
        self.partitions = partitions
        self.update()  # trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        width = rect.width()
        height = rect.height()

        painter.fillRect(rect, Qt.white)

        if not self.partitions:
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, "No Partitions Found")
            return

        total_size = sum(size for _, size in self.partitions)
        if total_size == 0:
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, "Partitions sizes are zero")
            return

        start_x = 10
        start_y = height // 3
        bar_height = height // 3
        gap = 5

        # Assign colors cycling through some colors
        colors = [
            QColor("#0078D7"), QColor("#E81123"), QColor("#107C10"),
            QColor("#FFB900"), QColor("#5C2D91"), QColor("#008272"),
            QColor("#FF8C00"), QColor("#E3008C"), QColor("#603CBA"),
        ]

        painter.setPen(QPen(Qt.black, 1))

        current_x = start_x
        for i, (part_num, size_mb) in enumerate(self.partitions):
            # Calculate width proportional to size
            part_width = max(int((size_mb / total_size) * (width - 2 * start_x)), 5)

            color = colors[i % len(colors)]
            painter.setBrush(color)
            painter.drawRect(current_x, start_y, part_width, bar_height)

            # Draw partition label centered
            painter.setPen(Qt.white)
            label = f"P{part_num}: {size_mb} MB"
            painter.drawText(current_x, start_y, part_width, bar_height, Qt.AlignCenter, label)

            current_x += part_width + gap
            painter.setPen(QPen(Qt.black, 1))


class VDPM(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Disk Partition Manager (DiskPart)")
        self.resize(900, 600)
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()

        self.tab_create = QWidget()
        self.tab_manage = QWidget()
        self.tab_info = QWidget()
        self.tab_logs = QWidget()

        self.tabs.addTab(self.tab_create, "📦 Create VHD")
        self.tabs.addTab(self.tab_manage, "🔌 Mount / Unmount")
        self.tabs.addTab(self.tab_info, "💾 Disk Info")
        self.tabs.addTab(self.tab_logs, "📋 Logs")

        self.init_create_tab()
        self.init_manage_tab()
        self.init_info_tab()
        self.init_logs_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # ---------- Create VHD Tab ----------
    def init_create_tab(self):
        layout = QVBoxLayout()
        title = QLabel("Create a VHD with Custom Partitions")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))

        self.total_size_input = QLineEdit()
        self.total_size_input.setPlaceholderText("Enter total VHD size in GB (e.g., 10)")
        self.total_size_input.setMinimumHeight(40)

        self.partition_input = QLineEdit()
        self.partition_input.setPlaceholderText("Enter partition sizes in GB (comma-separated, e.g., 2,3,5)")
        self.partition_input.setMinimumHeight(40)

        create_button = QPushButton("Create VHD with Partitions")
        create_button.setStyleSheet(self.button_style())
        create_button.setMinimumHeight(50)
        create_button.clicked.connect(self.create_custom_vhd_handler)

        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(self.total_size_input)
        layout.addWidget(self.partition_input)
        layout.addWidget(create_button)
        layout.addStretch()
        self.tab_create.setLayout(layout)

    # ---------- Mount/Unmount Tab ----------
    def init_manage_tab(self):
        layout = QVBoxLayout()
        title = QLabel("Attach or Detach Existing VHD Files")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))

        attach_button = QPushButton("Attach / Mount VHD")
        attach_button.setStyleSheet(self.button_style())
        attach_button.setMinimumHeight(50)
        attach_button.clicked.connect(self.attach_vhd_handler)

        detach_button = QPushButton("Detach / Unmount VHD")
        detach_button.setStyleSheet(self.button_style())
        detach_button.setMinimumHeight(50)
        detach_button.clicked.connect(self.detach_vhd_handler)

        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(attach_button)
        layout.addWidget(detach_button)
        layout.addStretch()
        self.tab_manage.setLayout(layout)

    # ---------- Disk Info Tab ----------
    def init_info_tab(self):
        layout = QVBoxLayout()
        label = QLabel("Disk Partition Map")
        label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(label)

        self.disk_map_widget = PartitionMapWidget()
        self.disk_map_widget.setMinimumHeight(150)
        self.disk_map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.disk_map_widget)

        self.disk_info_text = QTextEdit()
        self.disk_info_text.setReadOnly(True)
        self.disk_info_text.setStyleSheet("background-color: #f0f0f0; font-family: Consolas;")
        layout.addWidget(self.disk_info_text)

        refresh_button = QPushButton("Refresh Disk Info")
        refresh_button.setStyleSheet(self.button_style())
        refresh_button.setMinimumHeight(40)
        refresh_button.clicked.connect(self.load_disk_info)
        layout.addWidget(refresh_button)

        self.tab_info.setLayout(layout)

        # Load info on start
        self.load_disk_info()

    # ---------- Logs Tab ----------
    def init_logs_tab(self):
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #f0f0f0; font-family: Consolas;")
        layout.addWidget(self.log_output)
        self.tab_logs.setLayout(layout)

    # ---------- Helpers ----------
    def button_style(self):
        return """
        QPushButton {
            background-color: #0078D7;
            color: white;
            font-size: 16px;
            padding: 12px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #005a9e;
        }
        """

    def log(self, message):
        if hasattr(self, "log_output"):
            self.log_output.append(f"🕒 {message}")

    def run_diskpart_script(self, script):
        try:
            with open("temp_diskpart.txt", "w") as f:
                f.write(script)

            result = subprocess.run(
                ["diskpart", "/s", "temp_diskpart.txt"],
                capture_output=True, text=True
            )

            os.remove("temp_diskpart.txt")
            return result.stdout + result.stderr
        except Exception as e:
            return str(e)

    # ---------- VHD Creation Logic ----------
    def create_custom_vhd_handler(self):
        total_size = self.total_size_input.text().strip()
        partition_sizes = self.partition_input.text().strip()

        # Validate input
        if not total_size or not partition_sizes:
            QMessageBox.warning(self, "Input Missing", "Please fill in all fields.")
            return

        try:
            total_size_gb = int(total_size)
            parts = [int(p.strip()) for p in partition_sizes.split(',') if p.strip()]
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter only numbers.")
            return

        if sum(parts) > total_size_gb:
            QMessageBox.critical(self, "Size Error", "Partition sizes exceed total disk size!")
            return

        # Ask file location
        path, _ = QFileDialog.getSaveFileName(self, "Save VHD File", os.path.expanduser("~/Desktop"), "VHD Files (*.vhd)")
        if not path:
            return

        self.log(f"Creating VHD: {path}")
        fixed_path = f'"{os.path.normpath(path)}"'

        # Build diskpart script dynamically
        script = f"create vdisk file={fixed_path} maximum={total_size_gb * 1024} type=expandable\n"
        script += f"select vdisk file={fixed_path}\n"
        script += "attach vdisk\n"

        for i, size in enumerate(parts, start=1):
            script += f"create partition primary size={size * 1024}\n"
            script += "format fs=ntfs quick\n"
            script += "assign\n"

        output = self.run_diskpart_script(script)

        if "DiskPart successfully" in output:
            self.log("✅ VHD created with custom partitions.")
            QMessageBox.information(self, "Success", "VHD created and partitioned.")
            self.load_disk_info()
        else:
            self.log("❌ VHD creation failed.")
            self.log(output)
            QMessageBox.critical(self, "Failed", output)

    # ---------- Attach Logic ----------
    def attach_vhd_handler(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select VHD to Attach", os.path.expanduser("~/Desktop"), "VHD Files (*.vhd)")
        if path:
            self.log(f"Attaching VHD: {path}")
            fixed_path = f'"{os.path.normpath(path)}"'
            script = f"select vdisk file={fixed_path}\nattach vdisk"
            output = self.run_diskpart_script(script)
            if "DiskPart successfully attached" in output:
                self.log("✅ VHD attached successfully.")
                QMessageBox.information(self, "Success", "VHD attached.")
                self.load_disk_info()
            else:
                self.log("❌ Failed to attach VHD.")
                self.log(output)
                QMessageBox.critical(self, "Failed", output)

    # ---------- Detach Logic ----------
    def detach_vhd_handler(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select VHD to Detach", os.path.expanduser("~/Desktop"), "VHD Files (*.vhd)")
        if path:
            self.log(f"Detaching VHD: {path}")
            fixed_path = f'"{os.path.normpath(path)}"'
            script = f"select vdisk file={fixed_path}\ndetach vdisk"
            output = self.run_diskpart_script(script)
            if "DiskPart successfully detached" in output:
                self.log("✅ VHD detached successfully.")
                QMessageBox.information(self, "Success", "VHD detached.")
                self.load_disk_info()
            else:
                self.log("❌ Failed to detach VHD.")
                self.log(output)
                QMessageBox.critical(self, "Failed", output)

    # ---------- Disk Info Loading ----------
    def load_disk_info(self):
        self.log("Loading physical disk info...")
        script = "select disk 0\nlist partition"
        output = self.run_diskpart_script(script)

        self.disk_info_text.clear()

        partitions = []

        pattern = re.compile(
            r"Partition\s+(\d+)\s+\S+\s+(\d+)\s+(KB|MB|GB)", re.IGNORECASE
        )

        for line in output.splitlines():
            match = pattern.search(line)
            if match:
                part_num = int(match.group(1))
                size = int(match.group(2))
                unit = match.group(3).upper()

                if unit == "KB":
                    size_mb = size // 1024
                elif unit == "MB":
                    size_mb = size
                elif unit == "GB":
                    size_mb = size * 1024
                else:
                    size_mb = size

                partitions.append((part_num, size_mb))
                # Show info text
                self.disk_info_text.append(f"Partition {part_num}: {size} {unit} ({size_mb} MB)")

        if not partitions:
            self.log("No partitions found on Disk 0.")
            self.disk_info_text.append("No partitions found on Disk 0.")
            self.disk_map_widget.update_partitions([])
            return

        self.log(f"Found {len(partitions)} partitions on Disk 0.")
        self.disk_map_widget.update_partitions(partitions)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VDPM()
    window.show()
    sys.exit(app.exec_())
