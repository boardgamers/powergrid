"""Keep checkpoints paired with the exact meaning of their input features."""

FEATURE_REVISION = "3.1-uranium39"
METADATA_KEY = "powergrid.feature_revision"


def model_revision(model):
    return model.session.get_modelmeta().custom_metadata_map.get(METADATA_KEY, "3.0")


def check_revision(model, observed, allow_transfer=False):
    trained = model_revision(model)
    if trained != observed and not allow_transfer:
        raise ValueError(
            f"Feature revision mismatch: model {trained}, encoder {observed}"
        )


def embed_revision(path, revision=FEATURE_REVISION):
    import onnx

    model = onnx.load(str(path))
    props = {p.key: p.value for p in model.metadata_props}
    props[METADATA_KEY] = revision
    onnx.helper.set_model_props(model, props)
    onnx.save(model, str(path))
