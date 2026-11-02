import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

typedef PickedPhoto = ({String path, String name, int size});

/// Camera/gallery port (faked in widget tests).
abstract interface class PhotoPicker {
  Future<PickedPhoto?> camera();
  Future<List<PickedPhoto>> gallery({required int limit});

  /// Android may kill the activity while the camera is open; this returns
  /// photos taken before the restart so the selection isn't lost.
  Future<List<PickedPhoto>> recoverLost();
}

class ImagePickerPhotoPicker implements PhotoPicker {
  final _picker = ImagePicker();

  // Downscale on device: smaller uploads on weak mobile data, still well
  // above the server's low-resolution threshold.
  static const _maxSide = 2400.0;
  static const _quality = 85;

  Future<PickedPhoto> _toPicked(XFile f) async => (
    path: f.path,
    name: f.name,
    size: await f.length(),
  );

  @override
  Future<PickedPhoto?> camera() async {
    final f = await _picker.pickImage(
      source: ImageSource.camera,
      maxWidth: _maxSide,
      maxHeight: _maxSide,
      imageQuality: _quality,
    );
    return f == null ? null : _toPicked(f);
  }

  @override
  Future<List<PickedPhoto>> gallery({required int limit}) async {
    if (limit <= 0) return const [];
    final files =
        limit == 1
            ? [
              if (await _picker.pickImage(
                    source: ImageSource.gallery,
                    maxWidth: _maxSide,
                    maxHeight: _maxSide,
                    imageQuality: _quality,
                  )
                  case final f?)
                f,
            ]
            : await _picker.pickMultiImage(
              maxWidth: _maxSide,
              maxHeight: _maxSide,
              imageQuality: _quality,
              limit: limit,
            );
    return [for (final f in files) await _toPicked(f)];
  }

  @override
  Future<List<PickedPhoto>> recoverLost() async {
    if (defaultTargetPlatform != TargetPlatform.android) return const [];
    final lost = await _picker.retrieveLostData();
    if (lost.isEmpty) return const [];
    final files = lost.files ?? (lost.file == null ? <XFile>[] : [lost.file!]);
    return [for (final f in files) await _toPicked(f)];
  }
}

final photoPickerProvider = Provider<PhotoPicker>(
  (ref) => ImagePickerPhotoPicker(),
);
