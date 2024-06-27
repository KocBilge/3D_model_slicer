import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QOpenGLWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QVector3D
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from pywavefront import Wavefront

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self.sliced_model = None
        self.rotation = QVector3D(0, 0, 0)
        self.camera_position = QVector3D(0, 0, 5)
        self.selected_point = None
        self.hole_radius = 0.1
        self.support_height = 0.5
        self.models = []

        # Lighting parameters
        self.light_position = [5.0, 5.0, 5.0, 1.0]
        self.light_ambient = [0.2, 0.2, 0.2, 1.0]
        self.light_diffuse = [1.0, 1.0, 1.0, 1.0]
        self.light_specular = [1.0, 1.0, 1.0, 1.0]

        # Material parameters
        # Example: Adjusting material and lighting parameters
        self.mat_ambient = [0.5, 0.5, 0.5, 1.0]  # Adjust ambient material color
        self.mat_diffuse = [0.8, 0.8, 0.8, 1.0]  # Adjust diffuse material color
        self.mat_specular = [1.0, 1.0, 1.0, 1.0]  # Adjust specular material color
        self.mat_shininess = 120.0  # Adjust shininess for specular highlights


    def initializeGL(self):
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, self.light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, self.light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, self.light_specular)

        glMaterialfv(GL_FRONT, GL_AMBIENT, self.mat_ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, self.mat_diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, self.mat_specular)
        glMaterialfv(GL_FRONT, GL_SHININESS, self.mat_shininess)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluLookAt(self.camera_position.x(), self.camera_position.y(), self.camera_position.z(),
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

        glRotatef(self.rotation.x(), 1.0, 0.0, 0.0)
        glRotatef(self.rotation.y(), 0.0, 1.0, 0.0)
        glRotatef(self.rotation.z(), 0.0, 0.0, 1.0)

        self.draw_model()

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect_ratio = width / height
        gluPerspective(45, aspect_ratio, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def setModel(self, model_data):
        self.model = model_data
        self.slice_model()

    def draw_model(self):
        if not self.models:
            return

        for model in self.models:
            vertices, faces, position = model
            glPushMatrix()
            glTranslatef(position.x(), position.y(), position.z())
            glBegin(GL_TRIANGLES)
            for face in faces:
                normal = np.cross(np.array(vertices[face[1]]) - np.array(vertices[face[0]]),
                                  np.array(vertices[face[2]]) - np.array(vertices[face[0]]))
                normal = normal / np.linalg.norm(normal)
                glNormal3fv(normal)

                for vertex_id in face:
                    glVertex3fv(vertices[vertex_id])
            glEnd()
            glPopMatrix()

    def rotate_model(self, angle_x, angle_y, angle_z):
        self.rotation.setX(self.rotation.x() + angle_x)
        self.rotation.setY(self.rotation.y() + angle_y)
        self.rotation.setZ(self.rotation.z() + angle_z)
        self.update()

    def slice_model(self):
        if self.model is None:
            return

        vertices, faces = self.model

        sliced_vertices = vertices[:len(vertices) // 2]
        sliced_faces = []

        for face in faces:
            valid_face = []
            for vertex_id in face:
                if vertex_id < len(sliced_vertices):
                    valid_face.append(vertex_id)
            if len(valid_face) >= 3:
                sliced_faces.append(valid_face)

        self.sliced_model = (sliced_vertices, sliced_faces)
        self.update()

    def create_hole(self, position, radius):
        if self.sliced_model is None:
            return

        vertices, faces = self.sliced_model
        new_vertices = np.copy(vertices)

        for i, vertex in enumerate(vertices):
            vertex = QVector3D(*vertex)
            if vertex.distanceToPoint(position) <= radius:
                new_vertices[i] = [0, 0, 0]

        self.sliced_model = (new_vertices, faces)
        self.update()

    def create_support(self):
        if self.sliced_model is None:
            return

        vertices, faces = self.sliced_model
        min_z = min(vertex[2] for vertex in vertices)
        support_vertices = []

        for vertex in vertices:
            if vertex[2] == min_z:
                support_vertices.append(vertex + [self.support_height])
            else:
                support_vertices.append(vertex)

        self.sliced_model = (np.array(support_vertices), faces)
        self.update()

    def overflow_indicator(self):
        if self.sliced_model is None:
            return False

        vertices, _ = self.sliced_model
        max_x = max(vertex[0] for vertex in vertices)
        max_y = max(vertex[1] for vertex in vertices)
        max_z = max(vertex[2] for vertex in vertices)

        if max_x > 1.0 or max_y > 1.0 or max_z > 1.0:
            return True
        else:
            return False

    def set_camera_position(self, position):
        self.camera_position = position
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_W:
            self.camera_position.setZ(self.camera_position.z() - 0.1)
        elif key == Qt.Key_S:
            self.camera_position.setZ(self.camera_position.z() + 0.1)
        elif key == Qt.Key_A:
            self.camera_position.setX(self.camera_position.x() - 0.1)
        elif key == Qt.Key_D:
            self.camera_position.setX(self.camera_position.x() + 0.1)
        elif key == Qt.Key_Q:
            self.camera_position.setY(self.camera_position.y() + 0.1)
        elif key == Qt.Key_E:
            self.camera_position.setY(self.camera_position.y() - 0.1)
        self.update()

    def place_models(self, model_data, interval, count):
        self.models = []
        base_vertices, base_faces = model_data

        for i in range(count):
            position = QVector3D(i * interval, 0, 0)
            self.models.append((base_vertices, base_faces, position))

        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Model Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.glWidget = OpenGLWidget(self)
        self.setCentralWidget(self.glWidget)

        self.initUI()

    def initUI(self):
        control_layout = QVBoxLayout()
        self.create_control_buttons(control_layout)
        self.create_camera_controls(control_layout)
        self.create_overflow_indicator(control_layout)
        self.create_model_placement_controls(control_layout)
        self.create_view_controls(control_layout)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.glWidget)
        main_layout.addLayout(control_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.show()

    def create_control_buttons(self, layout):
        button_layout = QVBoxLayout()

        rotate_x_btn = QPushButton('Rotate X')
        rotate_x_btn.clicked.connect(lambda: self.rotate_model(10, 0, 0))
        button_layout.addWidget(rotate_x_btn)

        rotate_y_btn = QPushButton('Rotate Y')
        rotate_y_btn.clicked.connect(lambda: self.rotate_model(0, 10, 0))
        button_layout.addWidget(rotate_y_btn)

        rotate_z_btn = QPushButton('Rotate Z')
        rotate_z_btn.clicked.connect(lambda: self.rotate_model(0, 0, 10))
        button_layout.addWidget(rotate_z_btn)

        slice_btn = QPushButton('Slice Model')
        slice_btn.clicked.connect(self.slice_model)
        button_layout.addWidget(slice_btn)

        create_hole_btn = QPushButton('Create Hole')
        create_hole_btn.clicked.connect(self.create_hole_action)
        button_layout.addWidget(create_hole_btn)

        create_support_btn = QPushButton('Create Support')
        create_support_btn.clicked.connect(self.create_support_action)
        button_layout.addWidget(create_support_btn)

        layout.addLayout(button_layout)

    def create_camera_controls(self, layout):
        camera_layout = QHBoxLayout()
        camera_label = QLabel('Camera Position')
        camera_layout.addWidget(camera_label)

        self.camera_x_input = QLineEdit('0')
        self.camera_x_input.setFixedWidth(50)
        camera_layout.addWidget(self.camera_x_input)

        self.camera_y_input = QLineEdit('0')
        self.camera_y_input.setFixedWidth(50)
        camera_layout.addWidget(self.camera_y_input)

        self.camera_z_input = QLineEdit('5')
        self.camera_z_input.setFixedWidth(50)
        camera_layout.addWidget(self.camera_z_input)

        set_camera_btn = QPushButton('Set Camera')
        set_camera_btn.clicked.connect(self.set_camera_action)
        camera_layout.addWidget(set_camera_btn)

        layout.addLayout(camera_layout)

    def create_overflow_indicator(self, layout):
        overflow_label = QLabel('Overflow Indicator:')
        layout.addWidget(overflow_label)

        self.overflow_status = QLabel('Not Overflowing')
        layout.addWidget(self.overflow_status)

    def create_model_placement_controls(self, layout):
        placement_layout = QVBoxLayout()

        interval_label = QLabel('Model Interval:')
        placement_layout.addWidget(interval_label)

        self.interval_input = QLineEdit('1')
        self.interval_input.setFixedWidth(50)
        placement_layout.addWidget(self.interval_input)

        count_label = QLabel('Model Count:')
        placement_layout.addWidget(count_label)

        self.count_input = QLineEdit('1')
        self.count_input.setFixedWidth(50)
        placement_layout.addWidget(self.count_input)

        place_models_btn = QPushButton('Place Models')
        place_models_btn.clicked.connect(self.place_models_action)
        placement_layout.addWidget(place_models_btn)

        layout.addLayout(placement_layout)

    def create_view_controls(self, layout):
        view_layout = QVBoxLayout()

        view_top_btn = QPushButton('View Top')
        view_top_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(0, 5, 0)))
        view_layout.addWidget(view_top_btn)

        view_bottom_btn = QPushButton('View Bottom')
        view_bottom_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(0, -5, 0)))
        view_layout.addWidget(view_bottom_btn)

        view_front_btn = QPushButton('View Front')
        view_front_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(0, 0, 5)))
        view_layout.addWidget(view_front_btn)

        view_back_btn = QPushButton('View Back')
        view_back_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(0, 0, -5)))
        view_layout.addWidget(view_back_btn)

        view_left_btn = QPushButton('View Left')
        view_left_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(-5, 0, 0)))
        view_layout.addWidget(view_left_btn)

        view_right_btn = QPushButton('View Right')
        view_right_btn.clicked.connect(lambda: self.set_camera_position(QVector3D(5, 0, 0)))
        view_layout.addWidget(view_right_btn)

        layout.addLayout(view_layout)

    def rotate_model(self, angle_x, angle_y, angle_z):
        self.glWidget.rotate_model(angle_x, angle_y, angle_z)

    def slice_model(self):
        self.glWidget.slice_model()

    def create_hole_action(self):
        position = QVector3D(float(self.camera_x_input.text()), float(self.camera_y_input.text()), float(self.camera_z_input.text()))
        self.glWidget.create_hole(position, self.glWidget.hole_radius)

    def create_support_action(self):
        self.glWidget.create_support()

    def set_camera_action(self):
        position = QVector3D(float(self.camera_x_input.text()), float(self.camera_y_input.text()), float(self.camera_z_input.text()))
        self.glWidget.set_camera_position(position)

    def place_models_action(self):
        if self.glWidget.model is not None:
            interval = float(self.interval_input.text())
            count = int(self.count_input.text())
            self.glWidget.place_models(self.glWidget.model, interval, count)
        else:
            print("No model data set.")

    def update_overflow_indicator(self):
        if self.glWidget.overflow_indicator():
            self.overflow_status.setText('Overflowing')
        else:
            self.overflow_status.setText('Not Overflowing')

    def keyPressEvent(self, event):
        self.glWidget.keyPressEvent(event)
        self.update_overflow_indicator()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    sys.exit(app.exec_())
