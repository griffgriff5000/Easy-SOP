"""Graphics view for drawing and arranging editable design layers."""
from copy import deepcopy
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPixmap, QBrush, QPen
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem
from ..designs import new_layer, layer_image, layer_padding
from .canvas import image_pixmap


class DesignCanvas(QGraphicsView):
    def __init__(self, document, defaults, report_error):
        super().__init__()
        self.document=document;self.defaults=defaults;self.report_error=report_error
        self.setScene(QGraphicsScene(self));self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setMinimumSize(400,300);self.tool='select';self.zoom_factor=1;self.pan_anchor=None;self.items_by_id={};self.rebuilding=False
        self.start=None;self.path=[];self.preview=None;self.resizing=None
        self.scene().selectionChanged.connect(self.scene_selection)
        self.document.changed.connect(self.rebuild)
        self.document.selection_changed.connect(self.sync_selection)
        self.rebuild()

    def set_tool(self, tool):
        self.cancel_gesture();self.tool=tool
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag if tool=='select' else QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.ArrowCursor if tool=='select' else Qt.CursorShape.CrossCursor)

    def rebuild(self):
        self.rebuilding=True;self.preview=None;self.scene().clear();self.items_by_id={}
        for z,layer in enumerate(self.document.design['layers']):
            item=self.make_item(layer);item.setZValue(z)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,not layer['locked'])
            item.setData(0,layer['id']);item.setVisible(layer['visible'])
            self.items_by_id[layer['id']]=item
            item.setSelected(layer['id'] in self.document.selected)
        self.scene().setSceneRect(0,0,*self.document.design['size'])
        self.rebuilding=False;self.viewport().update()

    def make_item(self, layer):
        item=QGraphicsPixmapItem(image_pixmap(layer_image(layer)))
        padding=layer_padding(layer);item.setOffset(-padding,-padding)
        item.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        item.setPos(layer['x'],layer['y']);item.setTransformOriginPoint(layer['w']/2,layer['h']/2)
        item.setRotation(layer['rotation']);item.setOpacity(layer['opacity']/100)
        self.scene().addItem(item);return item

    def scene_selection(self):
        if self.rebuilding:return
        identities={item.data(0) for item in self.scene().selectedItems()}
        groups={row['group'] for row in self.document.design['layers'] if row['id'] in identities and row['group']}
        identities.update(row['id'] for row in self.document.design['layers'] if row['group'] in groups)
        self.document.set_selection(identities)

    def sync_selection(self):
        self.rebuilding=True
        for identity,item in self.items_by_id.items():item.setSelected(identity in self.document.selected)
        self.rebuilding=False;self.viewport().update()

    def fit_canvas(self):
        self.fitInView(self.sceneRect().adjusted(-15,-15,15,15),Qt.AspectRatioMode.KeepAspectRatio)
        self.scale(self.zoom_factor,self.zoom_factor)

    def set_zoom(self,factor):
        self.cancel_gesture();self.zoom_factor=max(1,min(4,float(factor or 1)));self.fit_canvas()

    def resizeEvent(self,event):
        super().resizeEvent(event);self.fit_canvas()

    def drawBackground(self,painter,rect):
        painter.fillRect(rect,QColor('#8897a3'))
        tile=QPixmap(24,24);tile.fill(QColor('#ffffff'))
        p=QPainter(tile);p.fillRect(0,0,12,12,QColor('#e6eaee'));p.fillRect(12,12,12,12,QColor('#e6eaee'));p.end()
        painter.fillRect(self.sceneRect(),QBrush(tile))

    def resize_grip(self):
        layers=self.document.selected_layers(editable=True)
        if len(layers)!=1 or len(self.document.selected)!=1:return None
        layer=layers[0];item=self.items_by_id.get(layer['id'])
        if not item:return None
        return layer,item.mapToScene(QPointF(layer['w'],layer['h']))

    def drawForeground(self,painter,rect):
        grip=self.resize_grip()
        if grip:
            point=grip[1];radius=5/max(.1,self.transform().m11())
            painter.setPen(QPen(QColor('#087f8c'),1));painter.setBrush(QColor('white'))
            painter.drawRect(QRectF(point.x()-radius,point.y()-radius,2*radius,2*radius))

    def point(self,event):
        p=self.mapToScene(event.position().toPoint());w,h=self.document.design['size']
        return QPointF(max(0,min(w,p.x())),max(0,min(h,p.y())))

    def candidate(self,end):
        x1,y1=self.start.x(),self.start.y();x2,y2=end.x(),end.y()
        if self.tool=='path':
            points=self.path+[end];xs=[p.x() for p in points];ys=[p.y() for p in points]
            left,top=min(xs),min(ys);w=max(1,max(xs)-left);h=max(1,max(ys)-top)
            coords=[[(p.x()-left)/w,(p.y()-top)/h] for p in points]
        else:
            left,top=min(x1,x2),min(y1,y2);w=max(1,abs(x2-x1));h=max(1,abs(y2-y1))
            coords=[[(x1-left)/w,(y1-top)/h],[(x2-left)/w,(y2-top)/h]] if self.tool in {'line','arrow'} else []
        return new_layer(self.tool,x=left,y=top,w=w,h=h,points=coords,**self.defaults())

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            if self.zoom_factor>1:self.pan_anchor=event.position();event.accept()
            return
        if event.button()!=Qt.MouseButton.LeftButton:return super().mousePressEvent(event)
        if self.tool!='select':
            if not self.sceneRect().contains(self.mapToScene(event.position().toPoint())):return
            self.start=self.point(event);self.path=[self.start];event.accept();return
        grip=self.resize_grip()
        if grip and math.dist((self.mapToScene(event.position().toPoint()).x(),self.mapToScene(event.position().toPoint()).y()),(grip[1].x(),grip[1].y())) <= 10/max(.1,self.transform().m11()):
            if hasattr(self,'resize_candidate'):del self.resize_candidate
            self.resizing=deepcopy(grip[0]);event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self.pan_anchor is not None:
            delta=event.position()-self.pan_anchor;self.pan_anchor=event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-round(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-round(delta.y()))
            event.accept();return
        if self.resizing:
            item=self.items_by_id[self.resizing['id']];point=item.mapFromScene(self.point(event))
            layer=deepcopy(self.resizing);layer['w']=max(1,min(2048,point.x()));layer['h']=max(1,min(2048,point.y()))
            item.setPixmap(image_pixmap(layer_image(layer)));self.resize_candidate=layer
            self.viewport().update();return
        if self.start is not None:
            end=self.point(event)
            if self.tool=='path' and len(self.path)<1999 and math.dist((end.x(),end.y()),(self.path[-1].x(),self.path[-1].y()))>=1:self.path.append(end)
            if self.preview:self.scene().removeItem(self.preview)
            self.preview=self.make_item(self.candidate(end));self.preview.setZValue(1000);return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan_anchor=None;event.accept();return
        if event.button()!=Qt.MouseButton.LeftButton:return super().mouseReleaseEvent(event)
        try:
            if self.resizing:
                candidate=getattr(self,'resize_candidate',self.resizing)
                self.document.update({'w':candidate['w'],'h':candidate['h']});self.cancel_gesture();self.rebuild();return
            if self.start is not None:
                end=self.point(event)
                if math.dist((self.start.x(),self.start.y()),(end.x(),end.y()))>=2 or (self.tool=='path' and len(self.path)>2):
                    layer=self.candidate(end);self.cancel_gesture();self.document.add(layer)
                else:self.cancel_gesture()
                return
            super().mouseReleaseEvent(event)
            candidate=deepcopy(self.document.design)
            group_moves={}
            for layer in candidate['layers']:
                item=self.items_by_id[layer['id']]
                dx,dy=item.pos().x()-layer['x'],item.pos().y()-layer['y']
                if layer['group'] and not layer['locked'] and (abs(dx)>.01 or abs(dy)>.01):group_moves[layer['group']]=(dx,dy)
            for layer in candidate['layers']:
                if layer['locked']:continue
                item=self.items_by_id[layer['id']]
                if not layer['visible'] and layer['group'] in group_moves:
                    dx,dy=group_moves[layer['group']];item.setPos(layer['x']+dx,layer['y']+dy)
                layer['x']=max(-4096,min(4096,item.pos().x()));layer['y']=max(-4096,min(4096,item.pos().y()))
            self.document.commit(candidate)
        except ValueError as exc:
            self.cancel_gesture();self.rebuild();self.report_error(str(exc))

    def cancel_gesture(self):
        if self.preview:
            self.scene().removeItem(self.preview);self.preview=None
        self.start=None;self.path=[];self.resizing=None
        if hasattr(self,'resize_candidate'):del self.resize_candidate

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.cancel_gesture();self.rebuild();event.accept()
        else:super().keyPressEvent(event)
