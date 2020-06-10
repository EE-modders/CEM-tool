ADDON_DIR=./src/blender_addon
ZIP_NAME="CEMtool-Blender_WiP11.zip"

addon:
	mkdir -p ${ADDON_DIR}/addon/io_scene_cem
	cp ${ADDON_DIR}/__pycache__/*.pyc ${ADDON_DIR}/addon/io_scene_cem/
	cd ${ADDON_DIR}/addon/ && zip -r ${ZIP_NAME} io_scene_cem/
	mv ${ADDON_DIR}/addon/${ZIP_NAME} .
clean:
	rm -rf ${ADDON_DIR}/addon
