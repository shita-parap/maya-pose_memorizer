# Maya PoseMemorizer
Maya Script  
Simple Pose copy & paste tool

![PoseMemoraizer_anim](https://user-images.githubusercontent.com/20962065/93213976-874c3280-f79f-11ea-82c3-4176d4b22668.gif)

## Install

`pose_memoraizer`フォルダをMayaのScriptフォルダにコピーしてください。  
または、Mayaの`PYTHONPATH`が通っているフォルダにコピーしてください。

## Usage
1. PoseMemorizerは下記のコマンドで起動してください。
```
import pose_memorizer
pose_memorizer.run()
```
2. transformノードを選択して、`Memoraize`ボタンを押してください。

3. ポーズを反転させたい場合は`Mirror`にチェックと各種パラメータを確認してください。

4. 適用させたいtransformノードを選択して、保存したPoseを選択してください。

5. `Apply`ボタンを押してください。


## Note

* Apply際に対象が無くてもダイアログ等は表示されません。
* Translate,Rotateのみです。Scaleは考慮しません。

## Author

* shita-parap
* Twitter : https://twitter.com/shita_parap


## License

"PoseMemorizer" is under [MIT license](https://en.wikipedia.org/wiki/MIT_License).